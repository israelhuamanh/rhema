import React from "react";
import { Activity, Waves } from "lucide-react";

interface LiveTranscriptProps {
  partialText: string;
  isConnected: boolean;
}

export const LiveTranscript: React.FC<LiveTranscriptProps> = ({
  partialText,
  isConnected,
}) => {
  return (
    <div className="bg-slate-900/70 border border-slate-800/90 rounded-2xl p-4 shadow-lg">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-amber-400/90">
          <Waves className="w-4 h-4" />
          <span>Monitor de Voz IA en Tiempo Real (Vosk Offline)</span>
        </div>
        <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
          <Activity className="w-3.5 h-3.5 text-emerald-400" />
          <span>16 kHz · Baja Latencia (&lt; 1.5s)</span>
        </div>
      </div>

      <div className="min-h-[56px] flex items-center bg-slate-950/80 border border-slate-800/80 rounded-xl px-4 py-3">
        {!isConnected ? (
          <p className="text-sm text-rose-400/90 italic">
            Esperando conexión con rhema-engine en ws://127.0.0.1:8765/ws...
          </p>
        ) : partialText ? (
          <p className="text-base md:text-lg font-medium text-slate-100 tracking-wide">
            “{partialText}”
          </p>
        ) : (
          <p className="text-sm text-slate-500 italic">
            Escuchando al predicador... (Ej: “Primera de Juan capítulo cuatro versículo ocho”)
          </p>
        )}
      </div>
    </div>
  );
};
