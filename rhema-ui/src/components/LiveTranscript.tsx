import React from "react";
import { Activity, Mic, MicOff, Sparkles, Waves } from "lucide-react";

interface LiveTranscriptProps {
  partialText: string;
  isConnected: boolean;
  isWebSpeechSupported?: boolean;
  isListeningWebSpeech?: boolean;
  onToggleWebSpeech?: () => void;
  onSampleSelect?: (ref: string) => void;
}

const QUICK_SAMPLES = [
  "Juan 3:16",
  "Salmos 23:1",
  "Filipenses 4:13",
  "Génesis 1:1",
  "Romanos 8:28",
  "Mateo 7:7",
];

export const LiveTranscript: React.FC<LiveTranscriptProps> = ({
  partialText,
  isConnected,
  isWebSpeechSupported = false,
  isListeningWebSpeech = false,
  onToggleWebSpeech,
  onSampleSelect,
}) => {
  return (
    <div className="bg-slate-900/70 border border-slate-800/90 rounded-2xl p-4 shadow-lg flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-amber-400/90">
          <Waves className="w-4 h-4" />
          <span>
            {isConnected
              ? "Monitor de Voz IA en Vivo (Vosk Offline)"
              : "Modo Demostración Web Interactivo"}
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
          <Activity
            className={`w-3.5 h-3.5 ${
              isConnected || isListeningWebSpeech
                ? "text-emerald-400 animate-pulse"
                : "text-amber-400"
            }`}
          />
          <span>
            {isConnected
              ? "Motor Local 16 kHz Conectado"
              : isListeningWebSpeech
              ? "Reconocimiento Web Activo"
              : "Demo Web"}
          </span>
        </div>
      </div>

      <div className="min-h-[56px] flex flex-col justify-center bg-slate-950/80 border border-slate-800/80 rounded-xl px-4 py-3">
        {isConnected ? (
          partialText ? (
            <p className="text-base md:text-lg font-medium text-slate-100 tracking-wide">
              “{partialText}”
            </p>
          ) : (
            <p className="text-sm text-slate-500 italic">
              Escuchando al predicador... (Ej: “Primera de Juan capítulo cuatro versículo ocho”)
            </p>
          )
        ) : (
          <div className="flex flex-col gap-1.5">
            {partialText ? (
              <p className="text-base font-medium text-amber-300">
                “{partialText}”
              </p>
            ) : isListeningWebSpeech ? (
              <p className="text-sm text-emerald-400 animate-pulse font-medium">
                🎙️ Escuchando tu voz... Di en voz alta: “San Juan tres dieciséis” o “Salmos veintitrés”.
              </p>
            ) : (
              <p className="text-xs md:text-sm text-slate-400">
                <span className="text-amber-400 font-semibold">Demo Web Activa:</span> Activa tu micrófono o haz clic en cualquier versículo de prueba para ver el proyector en vivo.
              </p>
            )}
          </div>
        )}
      </div>

      {/* Controles de Demo cuando no hay conexión local */}
      {!isConnected && (
        <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-slate-800/60">
          {isWebSpeechSupported && onToggleWebSpeech && (
            <button
              type="button"
              onClick={onToggleWebSpeech}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-bold transition shadow ${
                isListeningWebSpeech
                  ? "bg-rose-500 text-white animate-pulse"
                  : "bg-emerald-600 hover:bg-emerald-500 text-slate-950"
              }`}
            >
              {isListeningWebSpeech ? (
                <>
                  <MicOff className="w-3.5 h-3.5" />
                  Detener Micrófono
                </>
              ) : (
                <>
                  <Mic className="w-3.5 h-3.5" />
                  Hablar por Micrófono Web
                </>
              )}
            </button>
          )}

          {onSampleSelect && (
            <div className="flex items-center gap-1.5 overflow-x-auto py-1">
              <span className="text-[11px] font-semibold text-slate-400 flex items-center gap-1">
                <Sparkles className="w-3 h-3 text-amber-400" /> Probar:
              </span>
              {QUICK_SAMPLES.map((sample) => (
                <button
                  key={sample}
                  type="button"
                  onClick={() => onSampleSelect(sample)}
                  className="px-2 py-0.5 rounded-md text-[11px] font-medium bg-slate-800/80 hover:bg-amber-500 hover:text-slate-950 text-slate-300 border border-slate-700/60 transition"
                >
                  {sample}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
