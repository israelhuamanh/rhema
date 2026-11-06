import difflib
import re
import unicodedata
from typing import Dict, List, Optional, Tuple


# Diccionario canónico de los 66 libros de la Biblia (clave interna sin tildes -> Nombre canónico en BD)
CANONICAL_BOOKS: Dict[str, str] = {
    # Antiguo Testamento (39)
    "genesis": "Génesis",
    "exodo": "Éxodo",
    "levitico": "Levítico",
    "numeros": "Números",
    "deuteronomio": "Deuteronomio",
    "josue": "Josué",
    "jueces": "Jueces",
    "rut": "Rut",
    "1 samuel": "1 Samuel",
    "2 samuel": "2 Samuel",
    "1 reyes": "1 Reyes",
    "2 reyes": "2 Reyes",
    "1 cronicas": "1 Crónicas",
    "2 cronicas": "2 Crónicas",
    "esdras": "Esdras",
    "nehemias": "Nehemías",
    "ester": "Ester",
    "job": "Job",
    "salmos": "Salmos",
    "proverbios": "Proverbios",
    "eclesiastes": "Eclesiastés",
    "cantares": "Cantares",
    "isaias": "Isaías",
    "jeremias": "Jeremías",
    "lamentaciones": "Lamentaciones",
    "ezequiel": "Ezequiel",
    "daniel": "Daniel",
    "oseas": "Oseas",
    "joel": "Joel",
    "amos": "Amós",
    "abdias": "Abdías",
    "jonas": "Jonás",
    "miqueas": "Miqueas",
    "nahum": "Nahúm",
    "habacuc": "Habacuc",
    "sofonias": "Sofonías",
    "hageo": "Hageo",
    "zacarias": "Zacarías",
    "malaquias": "Malaquías",
    # Nuevo Testamento (27)
    "mateo": "Mateo",
    "marcos": "Marcos",
    "lucas": "Lucas",
    "juan": "Juan",
    "hechos": "Hechos",
    "romanos": "Romanos",
    "1 corintios": "1 Corintios",
    "2 corintios": "2 Corintios",
    "galatas": "Gálatas",
    "efesios": "Efesios",
    "filipenses": "Filipenses",
    "colosenses": "Colosenses",
    "1 tesalonicenses": "1 Tesalonicenses",
    "2 tesalonicenses": "2 Tesalonicenses",
    "1 timoteo": "1 Timoteo",
    "2 timoteo": "2 Timoteo",
    "tito": "Tito",
    "filemon": "Filemón",
    "hebreos": "Hebreos",
    "santiago": "Santiago",
    "1 pedro": "1 Pedro",
    "2 pedro": "2 Pedro",
    "1 juan": "1 Juan",
    "2 juan": "2 Juan",
    "3 juan": "3 Juan",
    "judas": "Judas",
    "apocalipsis": "Apocalipsis",
}

# Libros que admiten prefijo numérico (1, 2, 3)
NUMBERED_BOOK_BASES = (
    "samuel|reyes|cronicas|cronica|corintios|corintio|tesalonicenses|tesalonisenses|timoteo|pedro|juan"
)

# Sinónimos, variaciones habladas, introducciones litúrgicas y correcciones fonéticas de STT
BOOK_SYNONYMS: List[Tuple[str, str]] = [
    # Nombres compuestos y títulos litúrgicos
    (r"\bcantar de los cantares\b", "cantares"),
    (r"\bcantar de salomon\b", "cantares"),
    (r"\blos cantares\b", "cantares"),
    (r"\bhechos de los apostoles\b", "hechos"),
    (r"\blibro de los hechos\b", "hechos"),
    (r"\blamentaciones de jeremias\b", "lamentaciones"),
    (r"\bevangelio (?:segun )?(?:san )?mateo\b", "mateo"),
    (r"\bevangelio (?:segun )?(?:san )?marcos\b", "marcos"),
    (r"\bevangelio (?:segun )?(?:san )?lucas\b", "lucas"),
    (r"\bevangelio (?:segun )?(?:san )?juan\b", "juan"),
    (r"\bsan mateo\b", "mateo"),
    (r"\bsan marcos\b", "marcos"),
    (r"\bsan lucas\b", "lucas"),
    (r"\bsan juan\b", "juan"),
    (r"\bsan judas\b", "judas"),
    (r"\bsalmo\b", "salmos"),
    (r"\bproverbio\b", "proverbios"),
    (r"\brevelacion(?:es)?\b", "apocalipsis"),
    (r"\bapocalipsi\b", "apocalipsis"),
    # Variaciones fonéticas / singulares o errores frecuentes de voz/tipeo
    (r"\bgenersis\b", "genesis"),
    (r"\bjenesis\b", "genesis"),
    (r"\bgenes\b", "genesis"),
    (r"\becleciastes\b", "eclesiastes"),
    (r"\btesalonisenses\b", "tesalonicenses"),
    (r"\bcorintio\b", "corintios"),
    (r"\bcronica\b", "cronicas"),
    (r"\bcolosense\b", "colosenses"),
    (r"\bfilipense\b", "filipenses"),
    (r"\befesio\b", "efesios"),
    (r"\bgalata\b", "galatas"),
    (r"\bromano\b", "romanos"),
    (r"\bhebreo\b", "hebreos"),
    (r"\bjuez\b", "jueces"),
]


def _build_spoken_numbers_1_to_176() -> List[Tuple[re.Pattern, str]]:
    """
    Construye la lista ordenada de patrones Regex para transformar números hablados
    en español (del 1 al 176, cubriendo los 150 Salmos y los 176 versículos del Salmo 119)
    a dígitos, priorizando las frases compuestas más largas primero.
    """
    units = {
        1: ["uno", "un", "una", "primero", "primera"],
        2: ["dos", "segundo", "segunda"],
        3: ["tres", "tercero", "tercera"],
        4: ["cuatro", "cuarto", "cuarta"],
        5: ["cinco", "quinto", "quinta"],
        6: ["seis", "sexto", "sexta"],
        7: ["siete", "septimo", "septima"],
        8: ["ocho", "octavo", "octava"],
        9: ["nueve", "noveno", "novena"],
    }
    teens = {
        10: ["diez", "decimo", "decima"],
        11: ["once"],
        12: ["doce"],
        13: ["trece"],
        14: ["catorce"],
        15: ["quince"],
        16: ["dieciseis", "diez y seis"],
        17: ["diecisiete", "diez y siete"],
        18: ["dieciocho", "diez y ocho"],
        19: ["diecinueve", "diez y nueve"],
    }
    twenties = {
        20: ["veinte"],
        21: ["veintiuno", "veintiun", "veintiuna", "veinte y uno", "veinte y un"],
        22: ["veintidos", "veinte y dos"],
        23: ["veintitres", "veinte y tres"],
        24: ["veinticuatro", "veinte y cuatro"],
        25: ["veinticinco", "veinte y cinco"],
        26: ["veintiseis", "veinte y seis"],
        27: ["veintisiete", "veinte y siete"],
        28: ["veintiocho", "veinte y ocho"],
        29: ["veintinueve", "veinte y nueve"],
    }
    tens_names = {
        30: "treinta",
        40: "cuarenta",
        50: "cincuenta",
        60: "sesenta",
        70: "setenta",
        80: "ochenta",
        90: "noventa",
    }

    sub_hundred: Dict[str, int] = {}
    for num, words in units.items():
        for w in words:
            sub_hundred[w] = num
    for num, words in teens.items():
        for w in words:
            sub_hundred[w] = num
    for num, words in twenties.items():
        for w in words:
            sub_hundred[w] = num

    for ten_val, ten_word in tens_names.items():
        sub_hundred[ten_word] = ten_val
        for unit_val in range(1, 10):
            for unit_word in (
                ["uno", "un", "una"] if unit_val == 1 else [units[unit_val][0]]
            ):
                sub_hundred[f"{ten_word} y {unit_word}"] = ten_val + unit_val

    full_map: Dict[str, int] = dict(sub_hundred)
    full_map["cien"] = 100
    full_map["ciento"] = 100

    ordinal_words = {
        "primero", "primera", "segundo", "segunda", "tercero", "tercera",
        "cuarto", "cuarta", "quinto", "quinta", "sexto", "sexta",
        "septimo", "septima", "octavo", "octava", "noveno", "novena",
        "decimo", "decima",
    }

    for phrase, val in sub_hundred.items():
        if 1 <= val <= 76 and phrase not in ordinal_words:
            full_map[f"ciento {phrase}"] = 100 + val

    sorted_items = sorted(
        full_map.items(),
        key=lambda kv: (len(kv[0].split()), len(kv[0])),
        reverse=True,
    )

    compiled: List[Tuple[re.Pattern, str]] = []
    for phrase, number in sorted_items:
        pattern = re.compile(rf"\b{re.escape(phrase)}\b")
        compiled.append((pattern, str(number)))
    return compiled


SPOKEN_NUMBER_PATTERNS = _build_spoken_numbers_1_to_176()

# Conectores intermedios flexibles entre capítulo y versículo inicial:
# Soporta: "versiculos del", "del versiculo", "desde el versiculo", "en los versiculos",
# "versiculos", "versiculo", "versos del", "verso", "del", "desde el", "en el", etc.
_VERSE_INTRO_CONNECTOR = (
    r"(?:"
    r"(?:en\s+(?:el|los)\s+|alli\s+en\s+(?:el|los)\s+|leamos\s+(?:en\s+)?(?:el|los)\s+)?"
    r"(?:"
    r"(?:versiculos?|versos?)\s+(?:del\s+|desde\s+el\s+|numero\s+)?"
    r"|(?:del|desde\s+el|desde)\s+(?:versiculos?\s+|versos?\s+)?"
    r"|(?:en\s+el|el|con|punto|dos\s+puntos)\s+"
    r")"
    r")?"
)

# Conectores de rango entre versículo inicial y versículo final:
# Soporta: "al versiculo 9", "al verso 9", "al 9", "hasta el versiculo 9", "hasta el 9", "hasta 9", "y 5", "y el 5"
_RANGE_CONNECTOR = (
    r"(?:"
    r"(?:al|hasta\s+el|hasta|a\s+el|a)\s+(?:versiculos?\s+|versos?\s+)?"
    r"|y\s+(?:el\s+)?(?:versiculos?\s+|versos?\s+)?"
    r")"
)

# 1. Patrón Estándar con Rango (ej: "genesis capitulo 8 versiculos del 4 al 9", "genesis 8 del 4 al 9", "genesis capitulo 8 del versiculo 4 al versiculo 9")
PATTERN_RANGE_STANDARD = re.compile(
    rf"\b(?P<libro>[1-3]?\s?[a-z]+)\s+(?:capitulo\s+|cap\s+)?(?P<capitulo>\d+)\s+{_VERSE_INTRO_CONNECTOR}(?P<versiculo>\d+)\s+{_RANGE_CONNECTOR}(?P<versiculo_fin>\d+)\b"
)

# 2. Patrón Invertido con Rango (ej: "capitulo 8 de genesis versiculos del 4 al 9", "capitulo 8 de genesis del 4 al 9")
PATTERN_RANGE_INVERTED = re.compile(
    rf"\bcapitulo\s+(?P<capitulo>\d+)\s+de\s+(?:los\s+|las\s+|el\s+|la\s+)?(?P<libro>[1-3]?\s?[a-z]+)\s+{_VERSE_INTRO_CONNECTOR}(?P<versiculo>\d+)\s+{_RANGE_CONNECTOR}(?P<versiculo_fin>\d+)\b"
)

# 3. Patrón Estándar de Versículo Único (ej: "mateo capitulo 7 versiculo 8", "juan 6 3", "juan capitulo 6 en el 3")
PATTERN_SINGLE_STANDARD = re.compile(
    rf"\b(?P<libro>[1-3]?\s?[a-z]+)\s+(?:capitulo\s+|cap\s+)?(?P<capitulo>\d+)\s+{_VERSE_INTRO_CONNECTOR}(?P<versiculo>\d+)\b"
)

# 4. Patrón Invertido de Versículo Único (ej: "capitulo 7 de mateo versiculo 8", "capitulo 6 de juan 3")
PATTERN_SINGLE_INVERTED = re.compile(
    rf"\bcapitulo\s+(?P<capitulo>\d+)\s+de\s+(?:los\s+|las\s+|el\s+|la\s+)?(?P<libro>[1-3]?\s?[a-z]+)\s+{_VERSE_INTRO_CONNECTOR}(?P<versiculo>\d+)\b"
)

# 5. Patrón Invertido Total: Versículo primero, luego capítulo y libro (ej: "versiculo 8 del capitulo 7 de mateo")
PATTERN_VERSE_FIRST = re.compile(
    r"\b(?:versiculos?|versos?)\s+(?P<versiculo>\d+)(?:\s+(?:al|hasta\s+el|y)\s+(?P<versiculo_fin>\d+))?\s+(?:del\s+)?capitulo\s+(?P<capitulo>\d+)\s+de\s+(?:los\s+|las\s+|el\s+|la\s+)?(?P<libro>[1-3]?\s?[a-z]+)\b"
)

# 6. Patrón de Inicio de Capítulo (ej: "genesis capitulo 8 desde el principio" -> Génesis 8:1)
PATTERN_CHAPTER_START = re.compile(
    r"\b(?P<libro>[1-3]?\s?[a-z]+)\s+(?:capitulo\s+)?(?P<capitulo>\d+)\s+desde\s+el\s+(?:principio|comienzo|inicio)\b"
)

# 7. Patrones Contextuales (cuando el pastor ya está en un libro/capítulo y dice "versiculos del 10 al 12" o "versiculo 15")
PATTERN_CONTEXT_RANGE = re.compile(
    rf"\b(?:(?:versiculos?|versos?)\s+(?:del\s+|desde\s+el\s+)?|(?:del|desde\s+el)\s+(?:versiculos?\s+|versos?\s+)?)(?P<versiculo>\d+)\s+{_RANGE_CONNECTOR}(?P<versiculo_fin>\d+)\b"
)
PATTERN_CONTEXT_SINGLE = re.compile(
    r"\b(?:versiculo|verso)\s+(?:numero\s+)?(?P<versiculo>\d+)\b"
)


class VerseExtractor:
    """
    Motor de extracción de citas bíblicas basado en reglas (NLP/Regex) con soporte para:
    - Los 66 libros de la Biblia (con corrección fonética y de sinónimos).
    - Números hablados del 1 al 176.
    - Citas de versículo único y rangos de múltiples versículos ("del 4 al 9", "versículos 4 y 5", etc.).
    - Citas contextuales dentro del capítulo activo.
    """

    @staticmethod
    def strip_accents(text: str) -> str:
        """Elimina tildes y signos de puntuación manteniendo letras, dígitos y espacios."""
        normalized = unicodedata.normalize("NFD", text.lower())
        without_diacritics = "".join(
            ch for ch in normalized if unicodedata.category(ch) != "Mn"
        )
        cleaned = re.sub(r"[^a-z0-9\s]", " ", without_diacritics)
        return re.sub(r"\s+", " ", cleaned).strip()

    @classmethod
    def normalize_book_synonyms(cls, text: str) -> str:
        """
        Normaliza prefijos ordinales de libros ('primera de juan' -> '1 juan')
        y variaciones habladas o errores fonéticos ('genersis' -> 'genesis', 'salmo' -> 'salmos').
        """
        ordinal_prefixes = [
            (
                rf"\b(?:primera|primero|primer|uno|1)\s+(?:libro\s+de\s+|carta\s+(?:de\s+|a\s+los\s+)?|epistola\s+(?:de\s+|a\s+los\s+)?|de\s+)?(?P<book>{NUMBERED_BOOK_BASES})\b",
                r"1 \g<book>",
            ),
            (
                rf"\b(?:segunda|segundo|dos|2)\s+(?:libro\s+de\s+|carta\s+(?:de\s+|a\s+los\s+)?|epistola\s+(?:de\s+|a\s+los\s+)?|de\s+)?(?P<book>{NUMBERED_BOOK_BASES})\b",
                r"2 \g<book>",
            ),
            (
                rf"\b(?:tercera|tercero|tercer|tres|3)\s+(?:libro\s+de\s+|carta\s+(?:de\s+|a\s+los\s+)?|epistola\s+(?:de\s+|a\s+los\s+)?|de\s+)?(?P<book>{NUMBERED_BOOK_BASES})\b",
                r"3 \g<book>",
            ),
        ]
        for pattern, replacement in ordinal_prefixes:
            text = re.sub(pattern, replacement, text)

        for pattern, replacement in BOOK_SYNONYMS:
            text = re.sub(pattern, replacement, text)

        return re.sub(r"\s+", " ", text).strip()

    @classmethod
    def convert_spoken_numbers(cls, text: str) -> str:
        """Convierte números hablados en español (1 al 176) a dígitos."""
        for pattern, digit_str in SPOKEN_NUMBER_PATTERNS:
            text = pattern.sub(digit_str, text)
        return re.sub(r"\s+", " ", text).strip()

    @classmethod
    def preprocess(cls, raw_text: str) -> str:
        """Ejecuta la cadena completa de sanitización, sinónimos y conversión numérica."""
        step1 = cls.strip_accents(raw_text)
        step2 = cls.normalize_book_synonyms(step1)
        step3 = cls.convert_spoken_numbers(step2)
        step4 = cls.normalize_book_synonyms(step3)
        return step4

    @classmethod
    def _resolve_canonical_book(cls, raw_book: str) -> Optional[str]:
        """
        Resuelve el nombre canónico del libro bíblico (exacto o por similitud fonética/ortográfica
        para tolerar variaciones como 'genersis' -> 'Génesis').
        """
        cleaned = re.sub(r"\s+", " ", raw_book.strip())
        if cleaned in CANONICAL_BOOKS:
            return CANONICAL_BOOKS[cleaned]

        if " " in cleaned:
            last_token = cleaned.split()[-1]
            if last_token in CANONICAL_BOOKS:
                return CANONICAL_BOOKS[last_token]

        # Búsqueda difusa (fuzzy match >= 0.84) sólo para nombres de libros de >= 5 letras
        if len(cleaned) >= 5:
            matches = difflib.get_close_matches(
                cleaned, list(CANONICAL_BOOKS.keys()), n=1, cutoff=0.84
            )
            if matches:
                return CANONICAL_BOOKS[matches[0]]

        return None

    @classmethod
    def extract_range(
        cls,
        raw_text: str,
        context_book: Optional[str] = None,
        context_chapter: Optional[int] = None,
    ) -> Optional[Tuple[str, int, int, Optional[int]]]:
        """
        Extrae una cita bíblica completa (con soporte de rango de versículos).
        Retorna `(libro_canonico, capitulo, versiculo_inicio, versiculo_fin_opcional)`.
        Ejemplos:
          - "genesis capitulo 8 versiculos del 4 al 9" -> ('Génesis', 8, 4, 9)
          - "genesis 8 del 4 al 9"                     -> ('Génesis', 8, 4, 9)
          - "genersis capitulo 8 del versiculo 4 al versiculo 9" -> ('Génesis', 8, 4, 9)
          - "Juan seis tres"                           -> ('Juan', 6, 3, None)
        """
        if not raw_text or not raw_text.strip():
            return None

        processed = cls.preprocess(raw_text)

        # 1. Evaluar primero patrones de RANGO explícito
        last_range_match: Optional[Tuple[str, int, int, Optional[int]]] = None
        for pattern in (PATTERN_RANGE_STANDARD, PATTERN_RANGE_INVERTED):
            for match in pattern.finditer(processed):
                canonical_book = cls._resolve_canonical_book(match.group("libro"))
                chapter = int(match.group("capitulo"))
                v_start = int(match.group("versiculo"))
                v_end = int(match.group("versiculo_fin"))

                if (
                    canonical_book
                    and 1 <= chapter <= 150
                    and 1 <= v_start <= 176
                    and v_start <= v_end <= 176
                ):
                    last_range_match = (
                        canonical_book,
                        chapter,
                        v_start,
                        v_end if v_end > v_start else None,
                    )

        if last_range_match is not None:
            return last_range_match

        # 2. Evaluar patrón con versículo primero ("versiculo 8 del capitulo 7 de mateo")
        for match in PATTERN_VERSE_FIRST.finditer(processed):
            canonical_book = cls._resolve_canonical_book(match.group("libro"))
            chapter = int(match.group("capitulo"))
            v_start = int(match.group("versiculo"))
            v_end_raw = match.group("versiculo_fin")
            v_end = int(v_end_raw) if v_end_raw else None
            if canonical_book and 1 <= chapter <= 150 and 1 <= v_start <= 176:
                if v_end and v_end > v_start and v_end <= 176:
                    return (canonical_book, chapter, v_start, v_end)
                return (canonical_book, chapter, v_start, None)

        # 3. Evaluar patrones de VERSÍCULO ÚNICO (Estándar e Invertido)
        last_single_match: Optional[Tuple[str, int, int, Optional[int]]] = None
        for pattern in (PATTERN_SINGLE_STANDARD, PATTERN_SINGLE_INVERTED):
            for match in pattern.finditer(processed):
                canonical_book = cls._resolve_canonical_book(match.group("libro"))
                chapter = int(match.group("capitulo"))
                v_start = int(match.group("versiculo"))

                if canonical_book and 1 <= chapter <= 150 and 1 <= v_start <= 176:
                    last_single_match = (canonical_book, chapter, v_start, None)

        if last_single_match is not None:
            return last_single_match

        # 4. Evaluar inicio de capítulo ("genesis capitulo 8 desde el principio")
        for match in PATTERN_CHAPTER_START.finditer(processed):
            canonical_book = cls._resolve_canonical_book(match.group("libro"))
            chapter = int(match.group("capitulo"))
            if canonical_book and 1 <= chapter <= 150:
                return (canonical_book, chapter, 1, None)

        # 5. Evaluar referencias contextuales si ya hay un libro y capítulo activos en pantalla
        if context_book and context_chapter:
            for match in PATTERN_CONTEXT_RANGE.finditer(processed):
                v_start = int(match.group("versiculo"))
                v_end = int(match.group("versiculo_fin"))
                if 1 <= v_start <= 176 and v_start < v_end <= 176:
                    return (context_book, context_chapter, v_start, v_end)

            for match in PATTERN_CONTEXT_SINGLE.finditer(processed):
                v_start = int(match.group("versiculo"))
                if 1 <= v_start <= 176:
                    return (context_book, context_chapter, v_start, None)

        return None

    @classmethod
    def extract(cls, raw_text: str) -> Optional[Tuple[str, int, int]]:
        """
        Extrae la cita bíblica retornando la tupla clásica de 3 elementos `(libro, capitulo, versiculo_inicio)`
        para compatibilidad con los tests unitarios de la Fase 1.
        """
        res = cls.extract_range(raw_text)
        if res is None:
            return None
        book, chapter, v_start, _ = res
        return (book, chapter, v_start)


def extract_verse(raw_text: str) -> Optional[Tuple[str, int, int]]:
    """Función helper de conveniencia para extraer citas bíblicas (3-tupla)."""
    return VerseExtractor.extract(raw_text)


def extract_verse_range(
    raw_text: str,
    context_book: Optional[str] = None,
    context_chapter: Optional[int] = None,
) -> Optional[Tuple[str, int, int, Optional[int]]]:
    """Función helper para extraer citas bíblicas incluyendo rangos de versículos (4-tupla)."""
    return VerseExtractor.extract_range(
        raw_text, context_book=context_book, context_chapter=context_chapter
    )
