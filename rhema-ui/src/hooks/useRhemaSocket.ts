import { useCallback, useEffect, useRef, useState } from "react";
import type {
  AudioDevice,
  RhemaClientCommand,
  RhemaServerEvent,
  VersePayload,
} from "../types/rhema";

const WS_URL =
  (import.meta as any).env?.VITE_WS_URL || "ws://127.0.0.1:8765/ws";
const RECONNECT_DELAY_MS = 2000;

export interface UseRhemaSocketOptions {
  /** En Modo Automático, VERSE_DETECTED actualiza directamente el versículo proyectado */
  autoMode?: boolean;
}

export function useRhemaSocket(options: UseRhemaSocketOptions = {}) {
  const { autoMode = true } = options;
  const autoModeRef = useRef(autoMode);
  autoModeRef.current = autoMode;

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);

  const [isConnected, setIsConnected] = useState(false);
  const [partialText, setPartialText] = useState("");
  const [activeVerse, setActiveVerse] = useState<VersePayload | null>(null);
  const [pendingVerse, setPendingVerse] = useState<VersePayload | null>(null);
  const [detectedQueue, setDetectedQueue] = useState<VersePayload[]>([]);
  const [audioDevices, setAudioDevices] = useState<AudioDevice[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<number | null>(null);
  const [audioLevel, setAudioLevel] = useState<number>(0);
  const [searchResults, setSearchResults] = useState<VersePayload[]>([]);

  const sendCommand = useCallback((cmd: RhemaClientCommand) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(cmd));
    }
  }, []);

  const projectVerse = useCallback(
    (verse: VersePayload) => {
      setActiveVerse(verse);
      setPendingVerse((prev) =>
        prev?.reference === verse.reference ? null : prev
      );
      sendCommand({ command: "PROJECT_VERSE", payload: { verse } });
    },
    [sendCommand]
  );

  const dismissPendingVerse = useCallback(() => {
    setPendingVerse(null);
  }, []);

  const stepAdjacentVerse = useCallback(
    (step: number) => {
      sendCommand({ command: "ADJACENT_VERSE", payload: { step } });
    },
    [sendCommand]
  );

  const clearProjection = useCallback(() => {
    setActiveVerse(null);
    sendCommand({ command: "CLEAR_PROJECTION" });
  }, [sendCommand]);

  const changeAudioDevice = useCallback(
    (deviceId: number) => {
      setSelectedDeviceId(deviceId);
      sendCommand({
        command: "CHANGE_AUDIO_DEVICE",
        payload: { device_id: deviceId },
      });
    },
    [sendCommand]
  );

  const refreshAudioDevices = useCallback(() => {
    sendCommand({ command: "REQUEST_AUDIO_DEVICES" });
  }, [sendCommand]);

  const searchVerses = useCallback(
    (query: string) => {
      if (!query.trim()) {
        setSearchResults([]);
        return;
      }
      sendCommand({
        command: "SEARCH_VERSES",
        payload: { query },
      });
    },
    [sendCommand]
  );

  useEffect(() => {
    let isMounted = true;

    const connect = () => {
      if (!isMounted) return;
      try {
        const socket = new WebSocket(WS_URL);
        wsRef.current = socket;

        socket.onopen = () => {
          if (!isMounted) return;
          setIsConnected(true);
        };

        socket.onmessage = (msgEvent) => {
          if (!isMounted) return;
          try {
            const data = JSON.parse(msgEvent.data) as RhemaServerEvent;

            switch (data.event) {
              case "TRANSCRIPTION_PARTIAL":
                setPartialText(data.payload.text);
                break;

              case "VERSE_DETECTED": {
                const verse = data.payload;
                setDetectedQueue((prev) => {
                  const filtered = prev.filter(
                    (v) =>
                      v.reference !== verse.reference &&
                      !(
                        v.book === verse.book &&
                        v.chapter === verse.chapter &&
                        v.verse === verse.verse &&
                        !v.verse_end &&
                        Boolean(verse.verse_end)
                      )
                  );
                  return [verse, ...filtered].slice(0, 20);
                });

                if (autoModeRef.current) {
                  setActiveVerse(verse);
                  setPendingVerse(null);
                  if (socket.readyState === WebSocket.OPEN) {
                    socket.send(
                      JSON.stringify({
                        command: "PROJECT_VERSE",
                        payload: { verse },
                      })
                    );
                  }
                } else {
                  // En Modo Operador, colocar en tarjeta previa de aprobación
                  setPendingVerse(verse);
                }
                break;
              }

              case "VERSE_PROJECTED":
                setActiveVerse(data.payload);
                break;

              case "PROJECTION_CLEARED":
                setActiveVerse(null);
                break;

              case "AUDIO_DEVICES_LIST":
                setAudioDevices(data.payload);
                if (data.payload.length > 0) {
                  setSelectedDeviceId((prev) => prev ?? data.payload[0].id);
                }
                break;

              case "AUDIO_DEVICE_CHANGED":
                setSelectedDeviceId(data.payload.device_id);
                break;

              case "AUDIO_LEVEL":
                setAudioLevel(data.payload.level);
                break;

              case "SEARCH_RESULTS":
                setSearchResults(data.payload);
                break;
            }
          } catch {
            // Ignorar tramas malformadas
          }
        };

        socket.onclose = () => {
          if (!isMounted) return;
          setIsConnected(false);
          reconnectTimerRef.current = window.setTimeout(
            connect,
            RECONNECT_DELAY_MS
          );
        };

        socket.onerror = () => {
          socket.close();
        };
      } catch {
        reconnectTimerRef.current = window.setTimeout(
          connect,
          RECONNECT_DELAY_MS
        );
      }
    };

    connect();

    return () => {
      isMounted = false;
      if (reconnectTimerRef.current !== null) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return {
    isConnected,
    partialText,
    activeVerse,
    pendingVerse,
    detectedQueue,
    audioDevices,
    selectedDeviceId,
    audioLevel,
    searchResults,
    projectVerse,
    dismissPendingVerse,
    stepAdjacentVerse,
    clearProjection,
    changeAudioDevice,
    refreshAudioDevices,
    searchVerses,
  };
}
