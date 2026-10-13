import unittest
from datetime import date

from sintesis.render import render_email, render_subject


class RenderTest(unittest.TestCase):
    def test_escapes_note_html(self):
        html = render_email(
            "Cliente",
            date(2026, 9, 29),
            [
                {
                    "name": "Gobierno",
                    "items": [
                        {
                            "medium": "prensa",
                            "medium_label": "Prensa",
                            "outlet": "Diario",
                            "title": "<script>alert(1)</script>",
                            "body": "linea",
                            "url": "javascript:alert(1)",
                            "author": "",
                            "program": "",
                            "published_time": "07:00",
                        }
                    ],
                }
            ],
        )
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("javascript:", html)
        self.assertIn("Cliente", html)

    def test_subject_has_no_line_breaks(self):
        subject = render_subject("Hola\n{cliente} {fecha}", "Alcaldía", date(2026, 9, 29))
        self.assertEqual(subject, "Hola Alcaldía 29/09/2026")
        self.assertNotIn("\n", subject)


if __name__ == "__main__":
    unittest.main()
