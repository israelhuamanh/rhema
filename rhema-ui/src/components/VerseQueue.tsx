import React from "react";
import { BookOpen, CheckCircle2, Play, Sparkles } from "lucide-react";
import type { VersePayload } from "../types/rhema";

interface VerseQueueProps {
  queue: VersePayload[];
  activeVerse: VersePayload | null;
  autoMode: boolean;
  onProjectVerse: (verse: VersePayload) => void;
}

export const VerseQueue: React.FC<VerseQueueProps> = ({
  queue,
  activeVerse,
  autoMode,
  onProjectVerse,
}) => {
  return (
    <div className="bg-slate-900/70 border border-slate-800/90 rounded-2xl p-4 flex flex-col h-full">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-amber-400" />
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-200">
            Cola de Versículos Detectados
          </h2>
        </div>
        <span className="text-xs px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 font-medium">
          {queue.length} {queue.length === 1 ? "cita" : "citas"}
        </span>
      </div>

      {queue.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-center py-10 px-4 border border-dashed border-slate-800 rounded-xl text-slate-500">
          <BookOpen className="w-8 h-8 mb-2 text-slate-600" />
          <p className="text-sm font-medium text-slate-400">
            Aún no se han detectado citas bíblicas
          </p>
          <p className="text-xs mt-1 max-w-xs">
            Cuando el pastor mencione un libro, capítulo y versículo, aparecerá aquí instantáneamente.
          </p>
        </div>
      ) : (
        <div className="space-y-2.5 overflow-y-auto pr-1 max-h-[360px]">
          {queue.map((item, idx) => {
            const isLive = activeVerse?.reference === item.reference;
            const isPendingLatest = !autoMode && idx === 0 && !isLive;

            return (
              <div
                key={`${item.reference}-${item.timestamp}`}
                className={`group rounded-xl p-3.5 border transition-all ${
                  isLive
                    ? "bg-amber-500/10 border-amber-500/50 shadow-md"
                    : isPendingLatest
                    ? "bg-indigo-500/10 border-indigo-400/50 animate-pulse"
                    : "bg-slate-950/70 border-slate-800/80 hover:border-slate-700"
                }`}
              >
                <div className="flex items-center justify-between gap-2 mb-1.5">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-amber-400">
                      {item.reference}
                    </span>
                    <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                      {item.version}
                    </span>
                    {isLive && (
                      <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 rounded-full">
                        <CheckCircle2 className="w-3 h-3" /> EN PANTALLA
                      </span>
                    )}
                  </div>

                  <button
                    onClick={() => onProjectVerse(item)}
                    className={`inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg transition ${
                      isLive
                        ? "bg-slate-800 text-slate-300 hover:bg-slate-700"
                        : "bg-amber-500 text-slate-950 hover:bg-amber-400 shadow-sm"
                    }`}
                  >
                    <Play className="w-3.5 h-3.5 fill-current" />
                    {isLive ? "Re-proyectar" : "Proyectar"}
                  </button>
                </div>

                <p className="text-xs md:text-sm text-slate-300 line-clamp-2 leading-relaxed">
                  {item.text}
                </p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
