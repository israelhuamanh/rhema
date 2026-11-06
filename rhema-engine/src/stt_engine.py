import json
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional, Tuple

from vosk import KaldiRecognizer, Model, SetLogLevel

from src.audio_stream import AudioStream
from src.config import MODELS_DIR, SAMPLE_RATE, VOSK_MODEL_NAME, VOSK_MODEL_PATH
from src.verse_extractor import VerseExtractor

VOSK_MODEL_URL = f"https://alphacephei.com/vosk/models/{VOSK_MODEL_NAME}.zip"


def ensure_vosk_model(model_path: Path = VOSK_MODEL_PATH) -> Path:
    """
    Verifica que el modelo offline de Vosk exista en `rhema-engine/models/`.
    Si no está presente, lo descarga y descomprime automáticamente la primera vez.
    """
    if model_path.exists() and any(model_path.iterdir()):
        return model_path

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = MODELS_DIR / f"{VOSK_MODEL_NAME}.zip"

    print(f"[STTEngine] Modelo '{VOSK_MODEL_NAME}' no encontrado en {model_path}.")
    print(f"[STTEngine] Descargando desde {VOSK_MODEL_URL} (~39 MB)...")

    def _progress(block_num: int, block_size: int, total_size: int) -> None:
        if total_size > 0:
            downloaded = min(block_num * block_size, total_size)
            pct = (downloaded / total_size) * 100
            sys.stdout.write(f"\r  Descargando: {pct:5.1f}% ({downloaded // (1024 * 1024)} MB / {total_size // (1024 * 1024)} MB)")
            sys.stdout.flush()

    urllib.request.urlretrieve(VOSK_MODEL_URL, zip_path, reporthook=_progress)
    print("\n[STTEngine] Descomprimiendo modelo Vosk...")

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(MODELS_DIR)

    try:
        zip_path.unlink()
    except OSError:
        pass

    print(f"[STTEngine] Modelo listo en: {model_path}")
    return model_path


class STTEngine:
    """
    Wrapper del motor de reconocimiento de voz offline Vosk (`vosk-model-small-es-0.42`).
    """

    def __init__(
        self,
        model_path: Path = VOSK_MODEL_PATH,
        sample_rate: int = SAMPLE_RATE,
    ) -> None:
        # Silenciar logs verbosos de Kaldi
        SetLogLevel(-1)
        resolved_path = ensure_vosk_model(model_path)
        self.sample_rate = sample_rate
        self.model = Model(str(resolved_path))
        self.recognizer = KaldiRecognizer(self.model, float(self.sample_rate))

    def reset(self) -> None:
        """Reinicia el estado interno del reconocedor para una nueva frase."""
        self.recognizer.Reset()

    def process_chunk(self, audio_bytes: bytes) -> Tuple[bool, str]:
        """
        Procesa un bloque de audio PCM int16.
        Retorna `(es_final, texto)`.
        """
        if self.recognizer.AcceptWaveform(audio_bytes):
            res = json.loads(self.recognizer.Result())
            return True, res.get("text", "").strip()
        else:
            partial = json.loads(self.recognizer.PartialResult())
            return False, partial.get("partial", "").strip()


def run_console_prototype(device_id: Optional[int] = None) -> None:
    """
    Prototipo de consola de la Fase 1:
    Escucha el micrófono en tiempo real, transcribe con Vosk y extrae citas bíblicas.
    """
    print("=" * 68)
    print("  RHEMA ENGINE - FASE 1: Prototipo de Consola y Captura de Voz")
    print("=" * 68)

    devices = AudioStream.list_input_devices()
    print("\nMicrófonos detectados:")
    for dev in devices:
        print(f"  [ID {dev['id']}] {dev['name']}")

    print("\nInicializando modelo Vosk offline...")
    stt = STTEngine()
    stream = AudioStream()

    last_partial = ""
    last_detected_verse = None

    try:
        stream.start(device_id=device_id)
        print("\n🎙️  Escuchando micrófono... (Di una cita, ej: 'Primera de Juan capítulo cuatro versículo ocho')")
        print("   Presiona Ctrl+C para detener.\n")

        while True:
            chunk = stream.read_chunk(timeout=0.25)
            if chunk is None:
                continue

            is_final, text = stt.process_chunk(chunk)
            if not text:
                continue

            if not is_final:
                if text != last_partial:
                    last_partial = text
                    sys.stdout.write(f"\r\033[K💬 [Parcial]: {text}")
                    sys.stdout.flush()

                    # Extracción anticipada en parciales para ultra-baja latencia (< 1.5s)
                    detected = VerseExtractor.extract(text)
                    if detected and detected != last_detected_verse:
                        last_detected_verse = detected
                        book, ch, vs = detected
                        print(f"\n✨ [CITA DETECTADA EN VIVO]: ({book!r}, {ch}, {vs}) -> {book} {ch}:{vs}")
            else:
                last_partial = ""
                print(f"\r\033[K✅ [Final]:   {text}")
                detected = VerseExtractor.extract(text)
                if detected:
                    if detected != last_detected_verse:
                        book, ch, vs = detected
                        print(f"✨ [CITA DETECTADA]: ({book!r}, {ch}, {vs}) -> {book} {ch}:{vs}")
                    last_detected_verse = None
                else:
                    last_detected_verse = None

    except KeyboardInterrupt:
        print("\n\n[STTEngine] Captura finalizada por el usuario.")
    finally:
        stream.stop()


if __name__ == "__main__":
    run_console_prototype()
