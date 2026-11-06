import array
import math
import queue
import re
import sys
from typing import Any, Dict, List, Optional

import sounddevice as sd

from src.config import BLOCK_SIZE, CHANNELS, DTYPE, SAMPLE_RATE


class AudioStream:
    """
    Gestor de captura de audio en tiempo real mediante sounddevice.
    Captura exclusivamente de UN dispositivo físico seleccionado por ID,
    calcula el nivel de señal (vúmetro RMS) en tiempo real y aplica ganancia
    adaptativa suave para micrófonos con bajo volumen de entrada.
    """

    def __init__(
        self,
        sample_rate: int = SAMPLE_RATE,
        block_size: int = BLOCK_SIZE,
        channels: int = CHANNELS,
        dtype: str = DTYPE,
    ) -> None:
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.channels = channels
        self.dtype = dtype
        self.audio_queue: "queue.Queue[bytes]" = queue.Queue(maxsize=100)
        self._stream: Optional[sd.RawInputStream] = None
        self.current_device_id: Optional[int] = None
        self.current_level: int = 0  # 0..100 (Vúmetro en vivo)

    @staticmethod
    def _clean_device_label(raw_name: str) -> str:
        r"""
        Normaliza los nombres que Windows traduce de forma confusa:
        - 'Varios micrófonos (Realtek...)' (traducción literal de 'Microphone Array')
          -> 'Micrófono integrado (Realtek...)'
        - Limpia rutas de driver Bluetooth WDM-KS (@System32\drivers\...;(Nombre))
        """
        name = raw_name.strip()

        # Extraer nombre amigable si viene con ruta de driver WDM-KS (@System32...;(Device))
        bt_match = re.search(r";\(([^)]+)\)\)?$", name)
        if bt_match:
            dev_model = bt_match.group(1).strip()
            name = f"Auriculares con micrófono ({dev_model})"

        # Reemplazar la traducción literal confusa de Windows 'Varios micrófonos'
        name = re.sub(
            r"^varios\s+micr[oó]fonos\b",
            "Micrófono integrado",
            name,
            flags=re.IGNORECASE,
        )
        name = re.sub(
            r"^microphone\s+array\b",
            "Micrófono integrado",
            name,
            flags=re.IGNORECASE,
        )
        if "mic in at front panel" in name.lower():
            name = "Micrófono panel frontal (Jack 3.5mm)"

        return name

    @staticmethod
    def refresh_and_list_input_devices() -> List[Dict[str, Any]]:
        """Reinicializa el catálogo PortAudio para detectar interfaces USB conectadas en caliente."""
        try:
            sd._terminate()
            sd._initialize()
        except Exception:
            pass
        return AudioStream.list_input_devices()

    @staticmethod
    def list_input_devices() -> List[Dict[str, Any]]:
        """
        Retorna la lista de dispositivos físicos individuales de entrada (micrófonos / interfaces USB)
        en el formato del contrato WebSocket: [{"id": int, "name": str}].
        Excluye mezcladores virtuales ('Asignador de sonido', 'Controlador primario', 'Mezcla estéreo').
        """
        devices = sd.query_devices()
        default_hostapi = sd.default.hostapi

        # Nombres completos en DirectSound/WASAPI para restaurar nombres truncados a 31 chars en MME
        full_names = [
            str(d.get("name", "")).strip()
            for d in devices
            if d.get("max_input_channels", 0) > 0 and d.get("hostapi") != default_hostapi
        ]

        input_devices: List[Dict[str, Any]] = []
        seen_labels = set()

        for idx, dev in enumerate(devices):
            if dev.get("max_input_channels", 0) <= 0:
                continue
            if dev.get("hostapi") != default_hostapi:
                continue

            raw_name = str(dev.get("name", f"Dispositivo {idx}")).strip()
            lower_raw = raw_name.lower()

            # Excluir dispositivos virtuales/combinados del sistema operativo
            if any(
                skip in lower_raw
                for skip in (
                    "asignador de sonido",
                    "sound mapper",
                    "controlador primario",
                    "primary sound",
                    "mezcla est",
                    "stereo mix",
                    "altavoz de pc",
                )
            ):
                continue

            # Restaurar nombre si MME lo truncó a 31 caracteres
            resolved_name = raw_name
            for candidate in full_names:
                if candidate.startswith(raw_name) and len(candidate) > len(raw_name):
                    resolved_name = candidate
                    break

            clean_label = AudioStream._clean_device_label(resolved_name)
            if clean_label not in seen_labels:
                seen_labels.add(clean_label)
                input_devices.append({"id": idx, "name": clean_label})

        return input_devices

    def _audio_callback(
        self, indata: Any, frames: int, time_info: Any, status: sd.CallbackFlags
    ) -> None:
        """Callback ejecutado en subproceso nativo de PortAudio (sin bloqueo)."""
        if status:
            print(f"[AudioStream] Estado de audio: {status}", file=sys.stderr)

        raw_bytes = bytes(indata)

        # Calcular nivel RMS para el vúmetro y aplicar ganancia suave si la señal es baja
        try:
            samples = array.array("h")
            samples.frombytes(raw_bytes)
            if samples:
                # Muestreo rápido cada 4 samples para no consumir CPU
                subset = samples[::4]
                rms = math.sqrt(sum(s * s for s in subset) / len(subset))
                # Escala logarítmica/proporcional 0..100 para el indicador visual
                level = min(100, int((rms / 2500.0) * 100))
                self.current_level = level

                # Si hay voz con volumen bajo (ej. micrófono sin boost en Windows), amplificar x2.5
                if 80 < rms < 1800:
                    boosted = array.array(
                        "h",
                        (
                            max(-32768, min(32767, int(s * 2.5)))
                            for s in samples
                        ),
                    )
                    raw_bytes = boosted.tobytes()
        except Exception:
            pass

        try:
            self.audio_queue.put_nowait(raw_bytes)
        except queue.Full:
            try:
                self.audio_queue.get_nowait()
                self.audio_queue.put_nowait(raw_bytes)
            except queue.Empty:
                pass

    def start(self, device_id: Optional[int] = None) -> None:
        """
        Inicia la captura de audio exclusivamente en el dispositivo físico indicado.
        Si `device_id` es None, selecciona automáticamente el primer micrófono físico disponible.
        """
        self.stop()

        if device_id is None:
            available = self.list_input_devices()
            if available:
                device_id = available[0]["id"]

        self.current_device_id = device_id
        self._clear_queue()

        self._stream = sd.RawInputStream(
            samplerate=self.sample_rate,
            blocksize=self.block_size,
            device=device_id,
            dtype=self.dtype,
            channels=self.channels,
            callback=self._audio_callback,
        )
        self._stream.start()

    def stop(self) -> None:
        """Detiene y cierra el stream de audio activo."""
        self.current_level = 0
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as exc:
                print(f"[AudioStream] Error al cerrar stream: {exc}", file=sys.stderr)
            finally:
                self._stream = None

    def switch_device(self, device_id: Optional[int]) -> None:
        """Cambia en caliente el dispositivo único de entrada de audio."""
        self.start(device_id=device_id)

    def read_chunk(self, timeout: float = 0.25) -> Optional[bytes]:
        """Extrae el siguiente bloque de audio de la cola (None si expira el timeout)."""
        try:
            return self.audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def _clear_queue(self) -> None:
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break


if __name__ == "__main__":
    print("=== Dispositivos Físicos de Entrada de Audio ===")
    for dev in AudioStream.list_input_devices():
        print(f"  [ID {dev['id']}] {dev['name']}")
