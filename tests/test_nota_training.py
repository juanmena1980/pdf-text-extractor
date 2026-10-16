from __future__ import annotations

import unittest

from engines import get_engine


class TrainingRulesTest(unittest.TestCase):
    def test_separates_repeated_labels_and_drops_qr_prompt(self) -> None:
        engine = get_engine("nota_informativa")
        text = engine.correct_document(
            "ENLAS territorio sigue el programa\nESCANEA PARA LEER LA NOTA\nMUNDO/ sigue la nota"
        )
        self.assertIn("EN LAS territorio", text)
        self.assertNotIn("ENLAS", text)
        self.assertNotIn("ESCANEA", text.upper())
        self.assertIn("MUNDO / sigue", text)

    def test_banda_80_90_inserts_conjunctions_and_drops_photo_credit(self) -> None:
        engine = get_engine("nota_informativa")
        text = engine.correct_document(
            "El marcador quedó 80 98 al final.\n"
            "Argentina Perú, juegan el sábado.\n"
            "Foto: Bangkok Post el partido terminó en CDmx hoy."
        )
        self.assertIn("80 y 98", text)
        self.assertIn("Argentina y Perú,", text)
        self.assertIn("CDMX", text)
        self.assertNotIn("Foto: Bangkok Post", text)
        self.assertNotIn("CDmx", text)

    def test_banda_90_93_inserts_missing_word_and_splits_glue(self) -> None:
        engine = get_engine("nota_informativa")
        text = engine.correct_document(
            "Desde creación del programa siguió datosy Kejriwal en la nota."
        )
        self.assertIn("Desde su creación", text)
        self.assertIn("datos y", text)
        self.assertNotIn("datosy", text)

    def test_banda_93_96_normalizes_acronym(self) -> None:
        engine = get_engine("nota_informativa")
        text = engine.correct_document("El centro (CEnart), abrió la muestra.")
        self.assertIn("(CENART),", text)
        self.assertNotIn("CEnart", text)

    def test_banda_93_95_joins_brand_and_splits_group(self) -> None:
        engine = get_engine("nota_informativa")
        text = engine.correct_document(
            "La marca Stay Pro, sigue en el mercado y este grupocriminal quedó fuera."
        )
        self.assertIn("StayPro,", text)
        self.assertIn("Este grupo criminal", text)
        self.assertNotIn("grupocriminal", text)


if __name__ == "__main__":
    unittest.main()
