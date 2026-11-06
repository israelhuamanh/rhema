import time
import unittest

from src.db_manager import DBManager
from src.verse_extractor import VerseExtractor


class TestFase2DatabaseAndContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.db = DBManager()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.db.close()

    def test_exact_verse_queries_and_latency(self) -> None:
        t0 = time.perf_counter()
        mat = self.db.get_verse("Mateo", 7, 8)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        self.assertIsNotNone(mat)
        assert mat is not None
        self.assertEqual(mat["reference"], "Mateo 7:8")
        self.assertEqual(mat["book"], "Mateo")
        self.assertEqual(mat["chapter"], 7)
        self.assertEqual(mat["verse"], 8)
        self.assertEqual(
            mat["text"],
            "Porque todo aquel que pide, recibe; y el que busca, halla; y al que llama, se le abrirá.",
        )
        self.assertEqual(mat["version"], "RVR1960")
        self.assertLess(elapsed_ms, 10.0, f"La consulta tardó demasiado: {elapsed_ms:.2f} ms")
        print(f"  [Latencia SQLite] Mateo 7:8 consultado en {elapsed_ms:.3f} ms")

    def test_nlp_to_sqlite_pipeline(self) -> None:
        phrase = "hermanos leamos primera de juan capítulo cuatro versículo ocho"
        extracted = VerseExtractor.extract(phrase)
        self.assertEqual(extracted, ("1 Juan", 4, 8))
        assert extracted is not None

        record = self.db.get_verse(*extracted)
        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(record["reference"], "1 Juan 4:8")
        self.assertIn("Dios es amor", record["text"])
        print(f"  [Pipeline NLP -> SQLite] '{phrase}' -> {record['reference']}: \"{record['text']}\"")

    def test_manual_search(self) -> None:
        by_ref = self.db.search_manual("Salmos 23:1")
        self.assertEqual(len(by_ref), 1)
        self.assertEqual(by_ref[0]["reference"], "Salmos 23:1")

        by_text = self.db.search_manual("Jehová es mi pastor")
        self.assertTrue(any(r["reference"] == "Salmos 23:1" for r in by_text))

    def test_websocket_contract(self) -> None:
        import asyncio
        import json
        import threading
        import uvicorn
        import websockets
        from src.main import app

        config = uvicorn.Config(app, host="127.0.0.1", port=8766, log_level="error")
        server = uvicorn.Server(config)
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()

        async def _ws_client_check() -> None:
            # Esperar a que el servidor esté listo
            for _ in range(30):
                try:
                    async with websockets.connect("ws://127.0.0.1:8766/ws") as ws:
                        first_msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=3.0))
                        self.assertEqual(first_msg["event"], "AUDIO_DEVICES_LIST")
                        self.assertIsInstance(first_msg["payload"], list)
                        print(f"  [WebSocket] AUDIO_DEVICES_LIST recibido: {first_msg['payload']}")

                        await ws.send(
                            json.dumps(
                                {
                                    "command": "SEARCH_VERSES",
                                    "payload": {"query": "Mateo 7:8"},
                                }
                            )
                        )
                        # Leer hasta recibir SEARCH_RESULTS (ignorando parciales de micrófono si los hubiera)
                        for _ in range(10):
                            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=3.0))
                            if msg.get("event") == "SEARCH_RESULTS":
                                self.assertEqual(msg["payload"][0]["reference"], "Mateo 7:8")
                                break
                        return
                except OSError:
                    await asyncio.sleep(0.1)
            self.fail("No se pudo conectar al servidor WebSocket de prueba")

        try:
            asyncio.run(_ws_client_check())
        finally:
            server.should_exit = True
            thread.join(timeout=3.0)


if __name__ == "__main__":
    print("=== Ejecutando pruebas de la Fase 2 (SQLite RVR1960 + Pipeline) ===")
    unittest.main(verbosity=2)
