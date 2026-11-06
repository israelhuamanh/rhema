import json
import sqlite3
import sys
import urllib.request
from pathlib import Path
from typing import List, Tuple

# Permitir importar desde src/ cuando se ejecuta directamente
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import DB_PATH
from src.verse_extractor import CANONICAL_BOOKS

RVR1960_JSON_URL = (
    "https://raw.githubusercontent.com/thiagobodruk/bible/master/json/es_rvr1960.json"
)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS versiculos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    libro_id INTEGER NOT NULL,
    libro_nombre TEXT NOT NULL, -- Nombre normalizado: 'Mateo', '1 Juan', 'Salmos'
    capitulo INTEGER NOT NULL,
    versiculo INTEGER NOT NULL,
    texto TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_busqueda_rapida 
ON versiculos(libro_nombre, capitulo, versiculo);
"""

# Versículos de respaldo en caso de ejecutarse sin conexión a internet la primera vez
FALLBACK_VERSES: List[Tuple[int, str, int, int, str]] = [
    (1, "Génesis", 1, 1, "En el principio creó Dios los cielos y la tierra."),
    (19, "Salmos", 23, 1, "Jehová es mi pastor; nada me faltará."),
    (19, "Salmos", 119, 105, "Lámpara es a mis pies tu palabra, Y lumbrera a mi camino."),
    (40, "Mateo", 7, 8, "Porque todo aquel que pide, recibe; y el que busca, halla; y al que llama, se le abrirá."),
    (43, "Juan", 3, 16, "Porque de tal manera amó Dios al mundo, que ha dado a su Hijo unigénito, para que todo aquel que en él cree, no se pierda, mas tenga vida eterna."),
    (45, "Romanos", 8, 28, "Y sabemos que a los que aman a Dios, todas las cosas les ayudan a bien, esto es, a los que conforme a su propósito son llamados."),
    (50, "Filipenses", 4, 13, "Todo lo puedo en Cristo que me fortalece."),
    (62, "1 Juan", 4, 8, "El que no ama, no ha conocido a Dios; porque Dios es amor."),
]


def seed_database(db_path: Path = DB_PATH, force: bool = False) -> int:
    """
    Crea y puebla `biblia_rv1960.db` con los 66 libros y >31,100 versículos de la RVR1960.
    Retorna la cantidad total de versículos almacenados.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        cursor.executescript(SCHEMA_SQL)

        cursor.execute("SELECT COUNT(*) FROM versiculos")
        existing_count = cursor.fetchone()[0]
        if existing_count > 30000 and not force:
            print(f"[Seed] La base de datos ya está poblada con {existing_count:,} versículos en {db_path}.")
            return existing_count

        if existing_count > 0:
            cursor.execute("DELETE FROM versiculos")
            conn.commit()

        canonical_names = list(CANONICAL_BOOKS.values())
        rows_to_insert: List[Tuple[int, str, int, int, str]] = []

        try:
            print(f"[Seed] Descargando RVR1960 completa desde {RVR1960_JSON_URL}...")
            req = urllib.request.Request(
                RVR1960_JSON_URL, headers={"User-Agent": "RhemaEngine/1.0"}
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw_bytes = resp.read()
                bible_data = json.loads(raw_bytes.decode("utf-8-sig"))

            if len(bible_data) != 66:
                raise ValueError(f"Se esperaban 66 libros, pero el JSON contiene {len(bible_data)}")

            for book_idx, book_obj in enumerate(bible_data):
                libro_id = book_idx + 1
                libro_nombre = canonical_names[book_idx]
                chapters = book_obj.get("chapters", [])
                for chap_idx, verses_list in enumerate(chapters):
                    capitulo = chap_idx + 1
                    for verse_idx, verse_text in enumerate(verses_list):
                        versiculo = verse_idx + 1
                        clean_text = str(verse_text).strip()
                        rows_to_insert.append(
                            (libro_id, libro_nombre, capitulo, versiculo, clean_text)
                        )
        except Exception as exc:
            print(f"[Seed] Advertencia: No se pudo descargar el JSON completo ({exc}). Usando datos semilla de respaldo.")
            rows_to_insert = list(FALLBACK_VERSES)

        print(f"[Seed] Insertando {len(rows_to_insert):,} versículos en SQLite...")
        cursor.executemany(
            """
            INSERT INTO versiculos (libro_id, libro_nombre, capitulo, versiculo, texto)
            VALUES (?, ?, ?, ?, ?)
            """,
            rows_to_insert,
        )
        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM versiculos")
        total = cursor.fetchone()[0]
        print(f"[Seed] Base de datos lista en {db_path} ({total:,} versículos indexados).")
        return total
    finally:
        conn.close()


if __name__ == "__main__":
    seed_database()
