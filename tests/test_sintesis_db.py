import unittest
from datetime import datetime
from tempfile import TemporaryDirectory
from pathlib import Path

from sintesis import db, delivery
from sintesis.errors import ApiError


class SintesisDbTest(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(ignore_cleanup_errors=True)
        db.set_data_dir(Path(self.tmp.name))
        db.init_db()
        db.init_db()

    def tearDown(self):
        db.set_data_dir(None)
        self.tmp.cleanup()

    def test_keyword_weight_chooses_the_section(self):
        client_id = db.save_client({"name": "Municipio", "send_time": "08:00"})["id"]
        db.add_keyword(client_id, "alcalde", "Gobierno", 1)
        db.add_keyword(client_id, "obra", "Obra pública", 5)
        db.create_note(
            {
                "fecha": "2026-09-29",
                "medio": "prensa",
                "fuente": "El Diario",
                "titulo": "El alcalde supervisó la obra",
                "texto": "Recorrido por las calles.",
            }
        )
        db.create_note(
            {
                "fecha": "2026-09-29",
                "medio": "portal",
                "fuente": "Mercado",
                "titulo": "Sube el precio de la flor",
                "texto": "Nota de abasto sin relación.",
            }
        )
        view = db.desk(client_id, "2026-09-29")
        self.assertEqual([section["name"] for section in view["sections"]], ["Obra pública"])
        self.assertEqual(view["sections"][0]["items"][0]["match_phrase"], "obra")
        self.assertEqual(view["unassigned"][0]["title"], "Sube el precio de la flor")

    def test_discarded_notes_stay_out_of_the_email(self):
        client_id = self._client()
        db.add_keyword(client_id, "alcalde", "Gobierno", 1)
        db.create_note(
            {
                "fecha": "2026-09-29",
                "medio": "radio",
                "fuente": "Radio Centro",
                "titulo": "El alcalde en entrevista",
                "texto": "Declaraciones.",
            }
        )
        view = db.desk(client_id, "2026-09-29")
        synthesis_id = view["synthesis"]["id"]
        item_id = view["sections"][0]["items"][0]["item_id"]
        db.save_layout(
            synthesis_id,
            {"sections": [{"name": "Gobierno", "item_ids": []}], "discarded_ids": [item_id]},
        )
        self.assertEqual(db.document_model(synthesis_id)["sections"], [])

    def test_reorder_keeps_automatic_notes_until_the_section_changes(self):
        client_id = self._client()
        db.add_keyword(client_id, "alcalde", "Gobierno", 1)
        db.create_note(self._note("El alcalde explica en entrevista"))
        db.create_note(self._note("El alcalde inauguró la plaza"))
        view = db.desk(client_id, "2026-09-29")
        synthesis_id = view["synthesis"]["id"]
        first, second = view["sections"][0]["items"]
        db.save_layout(
            synthesis_id,
            {
                "sections": [{"name": "Gobierno", "item_ids": [second["item_id"], first["item_id"]]}],
                "discarded_ids": [],
            },
        )
        ordered = db.desk(client_id, "2026-09-29")["sections"][0]["items"]
        self.assertEqual([item["item_id"] for item in ordered], [second["item_id"], first["item_id"]])
        self.assertEqual({item["origin"] for item in ordered}, {"auto"})

        db.add_keyword(client_id, "entrevista", "Radio", 5)
        db.reclassify("2026-09-29", client_id)
        sections = {
            section["name"]: [item["title"] for item in section["items"]]
            for section in db.desk(client_id, "2026-09-29")["sections"]
        }
        self.assertIn("El alcalde explica en entrevista", sections["Radio"])
        self.assertIn("El alcalde inauguró la plaza", sections["Gobierno"])

    def test_empty_layout_cancels_a_scheduled_send(self):
        client_id = self._client()
        db.add_keyword(client_id, "alcalde", "Gobierno", 1)
        db.create_note(self._note("El alcalde anunció el plan"))
        view = db.desk(client_id, "2026-09-29")
        synthesis_id = view["synthesis"]["id"]
        item_id = view["sections"][0]["items"][0]["item_id"]
        db.mark_scheduled(synthesis_id, datetime(2030, 1, 1, 7, 50), datetime(2030, 1, 1, 6, 0))
        result = db.save_layout(
            synthesis_id,
            {"sections": [{"name": "Gobierno", "item_ids": []}], "discarded_ids": [item_id]},
        )
        self.assertTrue(result["schedule_cancelled"])
        self.assertEqual(result["desk"]["synthesis"]["status"], "borrador")

    def test_scheduler_claims_only_due_syntheses(self):
        client_id = self._client()
        db.add_keyword(client_id, "alcalde", "Gobierno", 1)
        db.create_note(self._note("El alcalde anunció el plan"))
        synthesis_id = db.desk(client_id, "2026-09-29")["synthesis"]["id"]
        db.mark_scheduled(synthesis_id, datetime(2099, 1, 1, 7, 50), datetime(2026, 9, 29, 6, 0))
        self.assertEqual(db.claim_due("2026-09-29T07:00:00"), [])
        db.mark_scheduled(synthesis_id, datetime(2020, 1, 1, 7, 50), datetime(2020, 1, 1, 6, 0))
        self.assertEqual(db.claim_due("2020-01-01T07:50:00"), [synthesis_id])
        self.assertEqual(db.desk(client_id, "2026-09-29")["synthesis"]["status"], "enviando")
        self.assertEqual(db.claim_due("2099-01-01T00:00:00"), [])

    def test_review_without_sender_does_not_schedule(self):
        client_id = self._client()
        db.add_recipient(client_id, "sala@example.com", "Sala")
        db.add_keyword(client_id, "alcalde", "Gobierno", 1)
        db.create_note(self._note("El alcalde anunció el plan"))
        synthesis_id = db.desk(client_id, "2026-09-29")["synthesis"]["id"]
        with self.assertRaises(ApiError):
            delivery.review(synthesis_id)
        self.assertEqual(db.desk(client_id, "2026-09-29")["synthesis"]["status"], "borrador")

    def test_manual_move_survives_reclassify(self):
        client_id = self._client()
        db.add_keyword(client_id, "alcalde", "Gobierno", 1)
        db.create_note(self._note("El alcalde visitó la colonia"))
        view = db.desk(client_id, "2026-09-29")
        item_id = view["sections"][0]["items"][0]["item_id"]
        db.save_layout(
            view["synthesis"]["id"],
            {
                "sections": [
                    {"name": "Gobierno", "item_ids": []},
                    {"name": "Cultura", "item_ids": [item_id]},
                ],
                "discarded_ids": [],
            },
        )
        db.reclassify("2026-09-29", client_id)
        sections = {
            section["name"]: [item["title"] for item in section["items"]]
            for section in db.desk(client_id, "2026-09-29")["sections"]
        }
        self.assertIn("El alcalde visitó la colonia", sections["Cultura"])
        self.assertEqual(sections["Gobierno"], [])

    def test_example_day_splits_notes_into_sections(self):
        result = db.load_example("2026-09-29")
        view = db.desk(result["client_id"], "2026-09-29")
        grouped = {
            section["name"]
            for section in view["sections"]
            if section["items"]
        }
        self.assertEqual(grouped, {"Obra pública", "Gobierno", "Seguridad", "Cultura"})
        self.assertEqual(
            view["unassigned"][0]["title"],
            "Sube el precio de la flor en el mercado de abasto",
        )

    def _client(self) -> int:
        return db.save_client({"name": "Municipio", "send_time": "08:00"})["id"]

    def _note(self, title: str) -> dict:
        return {
            "fecha": "2026-09-29",
            "medio": "prensa",
            "fuente": "El Diario",
            "titulo": title,
            "texto": "Cuerpo de la nota.",
        }


if __name__ == "__main__":
    unittest.main()
