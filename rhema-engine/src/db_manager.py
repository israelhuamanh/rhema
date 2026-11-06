import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from database.seed import seed_database
from src.config import BIBLE_VERSION, DB_PATH
from src.verse_extractor import CANONICAL_BOOKS, VerseExtractor

_SUPERSCRIPT_MAP = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")


def _to_superscript(num: int) -> str:
    return str(num).translate(_SUPERSCRIPT_MAP)


class DBManager:
    """
    Gestor de consultas indexadas en modo solo lectura sobre `biblia_rv1960.db`.
    Soporta tanto versículos individuales como rangos de múltiples versículos (ej. Génesis 8:4-9).
    """

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        if not self.db_path.exists():
            seed_database(self.db_path)

        # Abrir conexión SQLite en modo solo lectura e inmutable (compatible con C:\Program Files sin permisos de escritura)
        posix_path = self.db_path.resolve().as_posix()
        try:
            uri = f"file:{posix_path}?mode=ro&immutable=1"
            self._conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
        except sqlite3.Error:
            uri = f"file:{posix_path}?mode=ro"
            self._conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

    def get_verse(
        self,
        book: str,
        chapter: int,
        verse: int,
        verse_end: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Consulta un versículo exacto o un rango de versículos (`verse` .. `verse_end`)
        usando el índice `idx_busqueda_rapida(libro_nombre, capitulo, versiculo)`.
        """
        cursor = self._conn.cursor()

        if verse_end is not None and verse_end > verse:
            # Limitar un rango continuo a máximo 15 versículos para legibilidad en proyección
            capped_end = min(verse_end, verse + 14)
            cursor.execute(
                """
                SELECT libro_nombre, capitulo, versiculo, texto
                FROM versiculos
                WHERE libro_nombre = ? AND capitulo = ? AND versiculo >= ? AND versiculo <= ?
                ORDER BY versiculo ASC
                """,
                (book, chapter, verse, capped_end),
            )
            rows = cursor.fetchall()
            if not rows:
                return None

            if len(rows) == 1:
                row = rows[0]
                return {
                    "reference": f"{row['libro_nombre']} {row['capitulo']}:{row['versiculo']}",
                    "book": row["libro_nombre"],
                    "chapter": int(row["capitulo"]),
                    "verse": int(row["versiculo"]),
                    "text": row["texto"],
                    "version": BIBLE_VERSION,
                    "timestamp": int(time.time()),
                }

            first_v = int(rows[0]["versiculo"])
            last_v = int(rows[-1]["versiculo"])
            combined_text = " ".join(
                f"[{int(r['versiculo'])}] {r['texto']}" for r in rows
            )
            return {
                "reference": f"{rows[0]['libro_nombre']} {rows[0]['capitulo']}:{first_v}-{last_v}",
                "book": rows[0]["libro_nombre"],
                "chapter": int(rows[0]["capitulo"]),
                "verse": first_v,
                "verse_end": last_v,
                "text": combined_text,
                "version": BIBLE_VERSION,
                "timestamp": int(time.time()),
            }

        cursor.execute(
            """
            SELECT libro_nombre, capitulo, versiculo, texto
            FROM versiculos
            WHERE libro_nombre = ? AND capitulo = ? AND versiculo = ?
            LIMIT 1
            """,
            (book, chapter, verse),
        )
        row = cursor.fetchone()
        if row is None:
            return None

        return {
            "reference": f"{row['libro_nombre']} {row['capitulo']}:{row['versiculo']}",
            "book": row["libro_nombre"],
            "chapter": int(row["capitulo"]),
            "verse": int(row["versiculo"]),
            "text": row["texto"],
            "version": BIBLE_VERSION,
            "timestamp": int(time.time()),
        }

    def get_adjacent_verse(
        self, book: str, chapter: int, verse: int, step: int = 1
    ) -> Optional[Dict[str, Any]]:
        """
        Obtiene el versículo siguiente (+1) o anterior (-1) en orden bíblico canónico.
        """
        cursor = self._conn.cursor()
        cursor.execute(
            """
            SELECT id FROM versiculos
            WHERE libro_nombre = ? AND capitulo = ? AND versiculo = ?
            LIMIT 1
            """,
            (book, chapter, verse),
        )
        current = cursor.fetchone()
        if current is None:
            return None

        target_id = int(current["id"]) + step
        cursor.execute(
            """
            SELECT libro_nombre, capitulo, versiculo, texto
            FROM versiculos
            WHERE id = ?
            LIMIT 1
            """,
            (target_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None

        return {
            "reference": f"{row['libro_nombre']} {row['capitulo']}:{row['versiculo']}",
            "book": row["libro_nombre"],
            "chapter": int(row["capitulo"]),
            "verse": int(row["versiculo"]),
            "text": row["texto"],
            "version": BIBLE_VERSION,
            "timestamp": int(time.time()),
        }

    def search_manual(self, query: str, limit: int = 15) -> List[Dict[str, Any]]:
        """
        Buscador manual híbrido (para el operador en vivo):
        1. Soporta referencias individuales y con rango ('Génesis 8:4-9', 'Juan 3:16', 'mateo 7 8').
        2. Soporta lenguaje natural completo ('genesis capitulo 8 del 4 al 9').
        3. Soporta búsqueda por frase libre ('Jehová es mi pastor').
        """
        q = query.strip()
        if not q:
            return []

        # 1. Intentar formato abreviado "Libro cap:vers(-vers_fin)" o "Libro cap vers"
        ref_match = re.match(
            r"^\s*(?P<book>[1-3]?\s*[a-zA-ZáéíóúÁÉÍÓÚñÑ]+)\s+(?P<ch>\d+)(?:[:\s.,]+(?P<vs>\d+)(?:\s*[-aA]\s*(?P<ve>\d+))?)?\s*$",
            q,
        )
        if ref_match:
            raw_book_norm = VerseExtractor.normalize_book_synonyms(
                VerseExtractor.strip_accents(ref_match.group("book"))
            )
            canonical_book = CANONICAL_BOOKS.get(raw_book_norm)
            if not canonical_book:
                for k, v in CANONICAL_BOOKS.items():
                    if k.startswith(raw_book_norm):
                        canonical_book = v
                        break
            if not canonical_book:
                canonical_book = VerseExtractor._resolve_canonical_book(raw_book_norm)

            if canonical_book:
                ch = int(ref_match.group("ch"))
                vs_str = ref_match.group("vs")
                ve_str = ref_match.group("ve")
                cursor = self._conn.cursor()
                if vs_str is not None:
                    vs = int(vs_str)
                    ve = int(ve_str) if ve_str is not None else None
                    exact = self.get_verse(canonical_book, ch, vs, verse_end=ve)
                    return [exact] if exact else []
                else:
                    cursor.execute(
                        """
                        SELECT libro_nombre, capitulo, versiculo, texto
                        FROM versiculos
                        WHERE libro_nombre = ? AND capitulo = ?
                        ORDER BY versiculo ASC
                        LIMIT ?
                        """,
                        (canonical_book, ch, limit),
                    )
                    now = int(time.time())
                    return [
                        {
                            "reference": f"{r['libro_nombre']} {r['capitulo']}:{r['versiculo']}",
                            "book": r["libro_nombre"],
                            "chapter": int(r["capitulo"]),
                            "verse": int(r["versiculo"]),
                            "text": r["texto"],
                            "version": BIBLE_VERSION,
                            "timestamp": now,
                        }
                        for r in cursor.fetchall()
                    ]

        # 2. Intentar con el extractor de lenguaje natural (incluyendo rangos)
        extracted_range = VerseExtractor.extract_range(q)
        if extracted_range:
            b, ch, vs, ve = extracted_range
            exact = self.get_verse(b, ch, vs, verse_end=ve)
            if exact:
                return [exact]

        # 3. Búsqueda por contenido de texto
        cursor = self._conn.cursor()
        cursor.execute(
            """
            SELECT libro_nombre, capitulo, versiculo, texto
            FROM versiculos
            WHERE texto LIKE ?
            LIMIT ?
            """,
            (f"%{q}%", limit),
        )
        now = int(time.time())
        return [
            {
                "reference": f"{r['libro_nombre']} {r['capitulo']}:{r['versiculo']}",
                "book": r["libro_nombre"],
                "chapter": int(r["capitulo"]),
                "verse": int(r["versiculo"]),
                "text": r["texto"],
                "version": BIBLE_VERSION,
                "timestamp": now,
            }
            for r in cursor.fetchall()
        ]

    def close(self) -> None:
        if self._conn:
            self._conn.close()
