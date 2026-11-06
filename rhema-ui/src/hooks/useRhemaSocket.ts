import { useCallback, useEffect, useRef, useState } from "react";
import type {
  AudioDevice,
  RhemaClientCommand,
  RhemaServerEvent,
  VersePayload,
} from "../types/rhema";
import {
  DEMO_VERSES,
  matchSpokenVerseInDemo,
  searchDemoVerses,
} from "../services/demoVerseService";

const WS_URL =
  (import.meta as any).env?.VITE_WS_URL || "ws://127.0.0.1:8765/ws";
const RECONNECT_DELAY_MS = 3000;
const CHANNEL_NAME = "rhema_cross_tab_sync";
const STORAGE_KEY = "rhema_active_verse";

export interface UseRhemaSocketOptions {
  autoMode?: boolean;
}

export function useRhemaSocket(options: UseRhemaSocketOptions = {}) {
  const { autoMode = true } = options;
  const autoModeRef = useRef(autoMode);
  autoModeRef.current = autoMode;

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);
  const broadcastChannelRef = useRef<BroadcastChannel | null>(null);
  const recognitionRef = useRef<any>(null);

  const [isConnected, setIsConnected] = useState(false);
  const [partialText, setPartialText] = useState("");
  const [activeVerse, setActiveVerse] = useState<VersePayload | null>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });
  const [pendingVerse, setPendingVerse] = useState<VersePayload | null>(null);
  const [detectedQueue, setDetectedQueue] = useState<VersePayload[]>(DEMO_VERSES.slice(0, 4));
  const [audioDevices, setAudioDevices] = useState<AudioDevice[]>([
    { id: 0, name: "Micrófono Web / Navegador" },
  ]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<number | null>(0);
  const [audioLevel, setAudioLevel] = useState<number>(0);
  const [searchResults, setSearchResults] = useState<VersePayload[]>([]);
  const [isListeningWebSpeech, setIsListeningWebSpeech] = useState(false);

  const isWebSpeechSupported =
    typeof window !== "undefined" &&
    Boolean(
      (window as any).SpeechRecognition ||
        (window as any).webkitSpeechRecognition
    );

  const broadcastEvent = useCallback((event: RhemaServerEvent) => {
    try {
      if (broadcastChannelRef.current) {
        broadcastChannelRef.current.postMessage(event);
      }
    } catch {
      // Fallback
    }
  }, []);

  const sendCommand = useCallback((cmd: RhemaClientCommand) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(cmd));
    }
  }, []);

  const projectVerse = useCallback(
    (verse: VersePayload) => {
      setActiveVerse(verse);
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(verse));
      } catch {
        // ignore
      }
      setPendingVerse((prev) =>
        prev?.reference === verse.reference ? null : prev
      );
      sendCommand({ command: "PROJECT_VERSE", payload: { verse } });
      broadcastEvent({ event: "VERSE_PROJECTED", payload: verse });
    },
    [sendCommand, broadcastEvent]
  );

  const dismissPendingVerse = useCallback(() => {
    setPendingVerse(null);
  }, []);

  const clearProjection = useCallback(() => {
    setActiveVerse(null);
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      // ignore
    }
    sendCommand({ command: "CLEAR_PROJECTION" });
    broadcastEvent({ event: "PROJECTION_CLEARED", payload: {} });
  }, [sendCommand, broadcastEvent]);

  const stepAdjacentVerse = useCallback(
    (step: number) => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        sendCommand({ command: "ADJACENT_VERSE", payload: { step } });
        return;
      }
      // Demo fallback: mover entre versículos demo
      setActiveVerse((current) => {
        if (!current) return DEMO_VERSES[0];
        const currentIndex = DEMO_VERSES.findIndex(
          (v) => v.reference === current.reference
        );
        let nextIndex = currentIndex + step;
        if (nextIndex < 0) nextIndex = DEMO_VERSES.length - 1;
        if (nextIndex >= DEMO_VERSES.length) nextIndex = 0;
        const nextVerse = DEMO_VERSES[nextIndex];
        try {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(nextVerse));
        } catch {
          // ignore
        }
        broadcastEvent({ event: "VERSE_PROJECTED", payload: nextVerse });
        return nextVerse;
      });
    },
    [sendCommand, broadcastEvent]
  );

  const searchVerses = useCallback(
    (query: string) => {
      if (!query.trim()) {
        setSearchResults([]);
        return;
      }
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        sendCommand({ command: "SEARCH_VERSES", payload: { query } });
      } else {
        const results = searchDemoVerses(query);
        setSearchResults(results);
      }
    },
    [sendCommand]
  );

  const triggerSampleVerse = useCallback(
    (verse: VersePayload) => {
      setDetectedQueue((prev) => [verse, ...prev.filter((v) => v.reference !== verse.reference)].slice(0, 20));
      if (autoModeRef.current) {
        projectVerse(verse);
      } else {
        setPendingVerse(verse);
      }
    },
    [projectVerse]
  );

  // Reconocimiento de voz web para demo
  const stopWebSpeech = useCallback(() => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {
        // ignore
      }
      recognitionRef.current = null;
    }
    setIsListeningWebSpeech(false);
    setAudioLevel(0);
  }, []);

  const startWebSpeech = useCallback(() => {
    if (!isWebSpeechSupported) {
      alert("Tu navegador no soporta Web Speech API. Usa Google Chrome o Microsoft Edge para la demo de voz.");
      return;
    }
    stopWebSpeech();

    const SpeechRec =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;
    const recognition = new SpeechRec();
    recognition.lang = "es-ES";
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onstart = () => {
      setIsListeningWebSpeech(true);
      setAudioLevel(45);
    };

    recognition.onresult = (event: any) => {
      let interim = "";
      let final = "";

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          final += transcript;
        } else {
          interim += transcript;
        }
      }

      const textToShow = final || interim;
      setPartialText(textToShow);
      setAudioLevel(Math.min(95, 30 + Math.floor(Math.random() * 55)));

      const matched = matchSpokenVerseInDemo(textToShow);
      if (matched) {
        triggerSampleVerse(matched);
      }
    };

    recognition.onerror = () => {
      setIsListeningWebSpeech(false);
      setAudioLevel(0);
    };

    recognition.onend = () => {
      setIsListeningWebSpeech(false);
      setAudioLevel(0);
    };

    recognition.start();
    recognitionRef.current = recognition;
  }, [isWebSpeechSupported, stopWebSpeech, triggerSampleVerse]);

  const toggleWebSpeech = useCallback(() => {
    if (isListeningWebSpeech) {
      stopWebSpeech();
    } else {
      startWebSpeech();
    }
  }, [isListeningWebSpeech, startWebSpeech, stopWebSpeech]);

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

  // Sincronización entre pestañas (BroadcastChannel + Storage)
  useEffect(() => {
    try {
      const channel = new BroadcastChannel(CHANNEL_NAME);
      broadcastChannelRef.current = channel;

      channel.onmessage = (msgEvent) => {
        const data = msgEvent.data as RhemaServerEvent;
        if (data.event === "VERSE_PROJECTED") {
          setActiveVerse(data.payload);
        } else if (data.event === "PROJECTION_CLEARED") {
          setActiveVerse(null);
        }
      };
    } catch {
      // BroadcastChannel no disponible
    }

    const onStorage = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY) {
        if (e.newValue) {
          try {
            setActiveVerse(JSON.parse(e.newValue));
          } catch {
            // ignore
          }
        } else {
          setActiveVerse(null);
        }
      }
    };

    window.addEventListener("storage", onStorage);

    return () => {
      window.removeEventListener("storage", onStorage);
      if (broadcastChannelRef.current) {
        broadcastChannelRef.current.close();
      }
      stopWebSpeech();
    };
  }, [stopWebSpeech]);

  // WebSocket con rhema-engine
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
                setDetectedQueue((prev) => [verse, ...prev.filter((v) => v.reference !== verse.reference)].slice(0, 20));
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
                  broadcastEvent({ event: "VERSE_PROJECTED", payload: verse });
                } else {
                  setPendingVerse(verse);
                }
                break;
              }
              case "VERSE_PROJECTED":
                setActiveVerse(data.payload);
                broadcastEvent(data);
                break;
              case "PROJECTION_CLEARED":
                setActiveVerse(null);
                broadcastEvent(data);
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
            // Ignorar
          }
        };

        socket.onclose = () => {
          if (!isMounted) return;
          setIsConnected(false);
          reconnectTimerRef.current = window.setTimeout(connect, RECONNECT_DELAY_MS);
        };

        socket.onerror = () => {
          socket.close();
        };
      } catch {
        reconnectTimerRef.current = window.setTimeout(connect, RECONNECT_DELAY_MS);
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
  }, [broadcastEvent]);

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
    // Demo web features
    isWebSpeechSupported,
    isListeningWebSpeech,
    toggleWebSpeech,
    triggerSampleVerse,
  };
}
