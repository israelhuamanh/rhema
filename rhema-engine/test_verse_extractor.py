import unittest
from src.verse_extractor import (
    CANONICAL_BOOKS,
    VerseExtractor,
    extract_verse,
    extract_verse_range,
)


class TestVerseExtractor(unittest.TestCase):
    def test_prompt_mandatory_case(self):
        phrase = "hermanos leamos primera de juan capítulo cuatro versículo ocho"
        result = extract_verse(phrase)
        self.assertEqual(result, ("1 Juan", 4, 8))

    def test_multi_verse_range_patterns(self):
        range_cases = [
            (
                "genesis capitulo 8 versiculos del 4 al 9",
                ("Génesis", 8, 4, 9),
            ),
            (
                "genesis 8 del 4 al 9",
                ("Génesis", 8, 4, 9),
            ),
            (
                "genersis capitulo 8 del versiculo 4 al versiculo 9",
                ("Génesis", 8, 4, 9),
            ),
            (
                "génesis capítulo ocho desde el versículo cuatro hasta el versículo nueve",
                ("Génesis", 8, 4, 9),
            ),
            (
                "mateo capítulo siete versículos siete y ocho",
                ("Mateo", 7, 7, 8),
            ),
            (
                "juan tres del dieciséis al dieciocho",
                ("Juan", 3, 16, 18),
            ),
            (
                "capítulo ocho de génesis versículos del cuatro al nueve",
                ("Génesis", 8, 4, 9),
            ),
            (
                "versículos cuatro al nueve del capítulo ocho de génesis",
                ("Génesis", 8, 4, 9),
            ),
        ]
        for text, expected in range_cases:
            with self.subTest(text=text):
                self.assertEqual(extract_verse_range(text), expected)

    def test_contextual_patterns(self):
        self.assertEqual(
            extract_verse_range(
                "ahora leamos los versículos del diez al doce",
                context_book="Génesis",
                context_chapter=8,
            ),
            ("Génesis", 8, 10, 12),
        )
        self.assertEqual(
            extract_verse_range(
                "miren lo que dice el versículo quince",
                context_book="Génesis",
                context_chapter=8,
            ),
            ("Génesis", 8, 15, None),
        )

    def test_standard_patterns(self):
        cases = [
            ("Juan seis tres", ("Juan", 6, 3)),
            ("juan tres dieciséis", ("Juan", 3, 16)),
            ("mateo siete ocho", ("Mateo", 7, 8)),
            ("primera de juan cuatro ocho", ("1 Juan", 4, 8)),
            ("salmo veintitrés uno", ("Salmos", 23, 1)),
            ("vamos a abrir en mateo capítulo siete versículo ocho", ("Mateo", 7, 8)),
            ("leamos en san mateo siete verso ocho", ("Mateo", 7, 8)),
            ("abran sus biblias en salmo veintitrés versículo uno", ("Salmos", 23, 1)),
            ("en el salmo ciento diecinueve versículo ciento cinco", ("Salmos", 119, 105)),
            ("salmos ciento cincuenta versículo seis", ("Salmos", 150, 6)),
            ("segunda de corintios capítulo cinco verso diecisiete", ("2 Corintios", 5, 17)),
            ("tercera de juan capítulo uno versículo dos", ("3 Juan", 1, 2)),
            ("primero de reyes capítulo dieciocho versículo treinta y seis", ("1 Reyes", 18, 36)),
            ("cantar de los cantares capítulo dos versículo uno", ("Cantares", 2, 1)),
            ("hechos de los apóstoles capítulo dos versículo treinta y ocho", ("Hechos", 2, 38)),
            ("génesis capítulo uno versículo uno", ("Génesis", 1, 1)),
            ("génesis capítulo ocho desde el principio", ("Génesis", 8, 1)),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(extract_verse(text), expected)

    def test_inverted_patterns(self):
        cases = [
            ("capítulo siete de mateo versículo ocho", ("Mateo", 7, 8)),
            ("capítulo cuatro de primera de juan verso ocho", ("1 Juan", 4, 8)),
            ("capítulo veintitrés de salmos versículo uno", ("Salmos", 23, 1)),
            ("versículo ocho del capítulo siete de mateo", ("Mateo", 7, 8)),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(extract_verse(text), expected)

    def test_all_66_books_supported(self):
        self.assertEqual(len(CANONICAL_BOOKS), 66)
        for key, canonical_name in CANONICAL_BOOKS.items():
            phrase = f"leamos en {key} capitulo dos versiculo tres"
            self.assertEqual(
                VerseExtractor.extract(phrase),
                (canonical_name, 2, 3),
                f"Falló la detección para el libro: {key} -> {canonical_name}",
            )


if __name__ == "__main__":
    print("=== Ejecutando pruebas unitarias de verse_extractor.py ===")
    unittest.main(verbosity=2)
