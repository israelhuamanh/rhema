import React, { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { getCurrentWebviewWindow } from "@tauri-apps/api/webviewWindow";
import { Maximize2, X } from "lucide-react";
import { useRhemaSocket } from "../hooks/useRhemaSocket";
import type { VersePayload } from "../types/rhema";

export const ProjectorWindow: React.FC = () => {
  const { activeVerse } = useRhemaSocket({ autoMode: true });
  const [displayedVerse, setDisplayedVerse] = useState<VersePayload | null>(null);
  const [visible, setVisible] = useState(false);

  const stageRef = useRef<HTMLDivElement | null>(null);
  const contentRef = useRef<HTMLDivElement | null>(null);
  const quoteRef = useRef<HTMLQuoteElement | null>(null);
  const [fontSizePx, setFontSizePx] = useState<number>(56);

  const toggleFullscreen = async () => {
    try {
      await invoke("toggle_projector_fullscreen");
    } catch {
      try {
        const win = getCurrentWebviewWindow();
        const isFs = await win.isFullscreen();
        await win.setFullscreen(!isFs);
      } catch {
        // Ignorar fuera de Tauri
      }
    }
  };

  const hideProjector = async () => {
    try {
      await invoke("hide_projector_window");
    } catch {
      try {
        await getCurrentWebviewWindow().hide();
      } catch {
        // Ignorar
      }
    }
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "F11") {
        e.preventDefault();
        toggleFullscreen();
      } else if (e.key === "Escape") {
        try {
          getCurrentWebviewWindow().setFullscreen(false);
        } catch {
          // Ignorar
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (!activeVerse) {
      setVisible(false);
      const timer = window.setTimeout(() => setDisplayedVerse(null), 350);
      return () => clearTimeout(timer);
    }

    if (displayedVerse && displayedVerse.reference !== activeVerse.reference) {
      setVisible(false);
      const timer = window.setTimeout(() => {
        setDisplayedVerse(activeVerse);
        setVisible(true);
      }, 220);
      return () => clearTimeout(timer);
    } else {
      setDisplayedVerse(activeVerse);
      const timer = window.setTimeout(() => setVisible(true), 30);
      return () => clearTimeout(timer);
    }
  }, [activeVerse, displayedVerse]);

  // Cálculo inteligente de tamaño de fuente que aprovecha todo el espacio disponible
  // y garantiza matemáticamente que el texto y la cita nunca se salgan ni se descuadren.
  const fitTextToStage = useCallback(() => {
    const stage = stageRef.current;
    const content = contentRef.current;
    const quote = quoteRef.current;
    if (!stage || !content || !quote || !displayedVerse) return;

    const stageW = stage.clientWidth;
    const stageH = stage.clientHeight;
    if (stageW <= 0 || stageH <= 0) return;

    const len = displayedVerse.text.length;

    // Tamaño inicial balanceado proporcional a la pantalla y longitud del texto
    const minDim = Math.min(stageW, stageH * 1.38);
    let initialSize: number;
    if (len < 90) {
      initialSize = Math.round(minDim * 0.096);
    } else if (len < 180) {
      initialSize = Math.round(minDim * 0.083);
    } else if (len < 320) {
      initialSize = Math.round(minDim * 0.070);
    } else if (len < 550) {
      initialSize = Math.round(minDim * 0.058);
    } else if (len < 850) {
      initialSize = Math.round(minDim * 0.048);
    } else {
      initialSize = Math.round(minDim * 0.040);
    }

    // Limitar entre 18px y 80px
    let size = Math.max(18, Math.min(80, initialSize));
    quote.style.fontSize = `${size}px`;

    // Dejar siempre un margen vertical de respiro (~12% libre del escenario)
    const maxAllowedHeight = stageH * 0.88;
    while (size > 16 && content.scrollHeight > maxAllowedHeight) {
      size -= 2;
      quote.style.fontSize = `${size}px`;
    }

    setFontSizePx(size);
  }, [displayedVerse]);

  useLayoutEffect(() => {
    fitTextToStage();
  }, [fitTextToStage, displayedVerse]);

  useEffect(() => {
    const stage = stageRef.current;
    if (!stage) return;

    const observer = new ResizeObserver(() => {
      fitTextToStage();
    });
    observer.observe(stage);
    window.addEventListener("resize", fitTextToStage);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", fitTextToStage);
    };
  }, [fitTextToStage]);

  // Renderizar números de versículos en formato [4] con estilo de superíndice dorado
  const renderFormattedVerseText = (text: string) => {
    const parts = text.split(/(\[\d+\])/g);
    return parts.map((part, idx) => {
      const m = part.match(/^\[(\d+)\]$/);
      if (m) {
        return (
          <sup
            key={idx}
            className="font-sans font-bold text-amber-400 text-[0.58em] mr-1.5 ml-2 select-none"
          >
            {m[1]}
          </sup>
        );
      }
      return <React.Fragment key={idx}>{part}</React.Fragment>;
    });
  };

  return (
    <div
      data-tauri-drag-region
      onDoubleClick={toggleFullscreen}
      className="group w-screen h-screen overflow-hidden select-none bg-gradient-to-br from-slate-950 via-[#070b16] to-black text-white flex flex-col px-8 py-5 md:px-14 md:py-9 relative border border-slate-800/40"
    >
      {/* Resplandor ambiental sutil */}
      <div className="pointer-events-none absolute -top-40 left-1/2 -translate-x-1/2 w-[80vw] h-[45vh] bg-amber-500/5 blur-[130px] rounded-full" />

      {/* Encabezado minimalista compacto con controles flotantes al pasar el mouse */}
      <div
        data-tauri-drag-region
        className="shrink-0 flex items-center justify-between text-xs uppercase tracking-[0.35em] font-semibold z-20 mb-2"
      >
        <span data-tauri-drag-region className="opacity-35">
          RHEMA LIVE
        </span>

        <div className="flex items-center gap-3">
          <span
            data-tauri-drag-region
            className="opacity-30 hidden sm:inline text-[10px]"
          >
            DOBLE CLIC / F11: PANTALLA COMPLETA
          </span>

          {/* Botones discretos visibles al pasar el cursor por la ventana */}
          <div className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1.5 tracking-normal">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                toggleFullscreen();
              }}
              title="Alternar Pantalla Completa (F11)"
              className="p-1.5 rounded-lg bg-slate-900/80 hover:bg-amber-500 hover:text-slate-950 text-slate-300 border border-slate-700/70 transition"
            >
              <Maximize2 className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                hideProjector();
              }}
              title="Ocultar / Cerrar ventana del proyector (se puede reabrir desde Rhema Studio)"
              className="p-1.5 rounded-lg bg-slate-900/80 hover:bg-rose-500 hover:text-white text-slate-300 border border-slate-700/70 transition"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Escenario central aprovechando todo el ancho y alto disponible */}
      <div
        ref={stageRef}
        className="flex-1 min-h-0 w-full flex items-center justify-center overflow-hidden"
      >
        <div
          ref={contentRef}
          className={`w-full max-w-[88vw] mx-auto transition-all duration-500 ease-out transform ${
            visible && displayedVerse
              ? "opacity-100 translate-y-0 scale-100"
              : "opacity-0 translate-y-3 scale-[0.98]"
          }`}
        >
          {displayedVerse ? (
            <div className="flex flex-col items-center justify-center text-center gap-5 md:gap-7">
              <blockquote
                ref={quoteRef}
                style={{
                  fontSize: `${fontSizePx}px`,
                  lineHeight: displayedVerse.text.length > 350 ? 1.32 : 1.24,
                  textWrap: "balance",
                }}
                className="font-serif font-medium text-slate-50 drop-shadow-[0_4px_24px_rgba(0,0,0,0.85)] w-full break-words"
              >
                “{renderFormattedVerseText(displayedVerse.text)}”
              </blockquote>

              <div className="shrink-0 flex items-center justify-center gap-4 pt-1">
                <div className="h-[2px] w-12 md:w-16 bg-amber-400/70 rounded-full" />
                <cite
                  style={{
                    fontSize: `${Math.max(16, Math.min(40, Math.round(fontSizePx * 0.56)))}px`,
                  }}
                  className="not-italic font-bold tracking-wide text-amber-400 uppercase drop-shadow leading-none"
                >
                  {displayedVerse.reference}
                </cite>
                <span className="text-xs md:text-base font-semibold px-3 py-1 rounded-full bg-amber-500/15 border border-amber-400/40 text-amber-300 leading-none">
                  {displayedVerse.version}
                </span>
                <div className="h-[2px] w-12 md:w-16 bg-amber-400/70 rounded-full" />
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center text-center opacity-20">
              <p className="text-xl md:text-3xl tracking-[0.25em] uppercase font-light text-slate-400">
                Rhema · Proyección Bíblica en Vivo
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
