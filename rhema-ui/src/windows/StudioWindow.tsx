import React, { useCallback, useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import {
  Check,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  EyeOff,
  Maximize2,
  Monitor,
  MonitorOff,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  X,
  Zap,
} from "lucide-react";
import { AudioSelector } from "../components/AudioSelector";
import { LiveTranscript } from "../components/LiveTranscript";
import { VerseQueue } from "../components/VerseQueue";
import { useRhemaSocket } from "../hooks/useRhemaSocket";
import type { VersePayload } from "../types/rhema";

export const StudioWindow: React.FC = () => {
  const [autoMode, setAutoMode] = useState(true);
  const [manualQuery, setManualQuery] = useState("");
  const [projectorOpen, setProjectorOpen] = useState(true);
  const [projectorFullscreen, setProjectorFullscreen] = useState(false);

  const {
    isConnected,
    partialText,
    activeVerse,
    pendingVerse,
    detectedQueue,
    audioDevices,
    selectedDeviceId,
    audioLevel,
    searchResults,
    projectVerse: rawProjectVerse,
    dismissPendingVerse,
    stepAdjacentVerse,
    clearProjection,
    changeAudioDevice,
    refreshAudioDevices,
    searchVerses,
  } = useRhemaSocket({ autoMode });

  const syncProjectorStatus = useCallback(async () => {
    try {
      const status = await invoke<{ isOpen: boolean; isFullscreen: boolean }>(
        "get_projector_status"
      );
      setProjectorOpen(status.isOpen);
      setProjectorFullscreen(status.isFullscreen);
    } catch {
      // Fuera de Tauri
    }
  }, []);

  useEffect(() => {
    syncProjectorStatus();
    const timer = window.setInterval(syncProjectorStatus, 1200);
    return () => clearInterval(timer);
  }, [syncProjectorStatus]);

  const handleOpenProjector = useCallback(async () => {
    try {
      const status = await invoke<{ isOpen: boolean; isFullscreen: boolean }>(
        "open_projector_window"
      );
      setProjectorOpen(status.isOpen);
      setProjectorFullscreen(status.isFullscreen);
    } catch {
      // Ignorar
    }
  }, []);

  const handleHideProjector = useCallback(async () => {
    try {
      const status = await invoke<{ isOpen: boolean; isFullscreen: boolean }>(
        "hide_projector_window"
      );
      setProjectorOpen(status.isOpen);
      setProjectorFullscreen(status.isFullscreen);
    } catch {
      // Ignorar
    }
  }, []);

  const handleToggleProjectorFullscreen = useCallback(async () => {
    try {
      const status = await invoke<{ isOpen: boolean; isFullscreen: boolean }>(
        "toggle_projector_fullscreen"
      );
      setProjectorOpen(status.isOpen);
      setProjectorFullscreen(status.isFullscreen);
    } catch {
      // Ignorar
    }
  }, []);

  // Al proyectar manualmente un versículo, asegurarse de que la ventana del proyector esté abierta
  const projectVerse = useCallback(
    (verse: VersePayload) => {
      rawProjectVerse(verse);
      if (!projectorOpen) {
        handleOpenProjector();
      }
    },
    [rawProjectVerse, projectorOpen, handleOpenProjector]
  );

  // Atajos de teclado de producción en vivo
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const tag = document.activeElement?.tagName;
      if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA") {
        return;
      }

      if (e.code === "Space" && !autoMode) {
        const candidate = pendingVerse ?? detectedQueue[0];
        if (candidate) {
          e.preventDefault();
          projectVerse(candidate);
        }
      } else if (e.code === "ArrowRight" && activeVerse) {
        e.preventDefault();
        stepAdjacentVerse(1);
      } else if (e.code === "ArrowLeft" && activeVerse) {
        e.preventDefault();
        stepAdjacentVerse(-1);
      }
    };
    window.addEventListener("keydown", onKeyDownWrapper);
    function onKeyDownWrapper(ev: KeyboardEvent) {
      handleKeyDown(ev);
    }
    return () => window.removeEventListener("keydown", onKeyDownWrapper);
  }, [
    autoMode,
    pendingVerse,
    detectedQueue,
    activeVerse,
    projectVerse,
    stepAdjacentVerse,
  ]);

  const handleManualSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchResults.length > 0) {
      projectVerse(searchResults[0]);
    } else {
      searchVerses(manualQuery);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Barra Superior de Producción */}
      <header className="border-b border-slate-800/90 bg-slate-900/60 backdrop-blur px-6 py-3.5 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-amber-500/15 border border-amber-500/40 flex items-center justify-center text-amber-400 font-bold text-lg">
            ῥ
          </div>
          <div>
            <h1 className="text-base font-bold tracking-wide text-slate-100 flex items-center gap-2">
              RHEMA STUDIO
              <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30">
                Producción en Vivo
              </span>
            </h1>
            <p className="text-xs text-slate-400">
              Proyector Bíblico Automatizado · 100% Local
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Control directo de la Ventana del Proyector (Abrir / Ocultar) */}
          {projectorOpen ? (
            <div className="flex items-center gap-1.5 bg-slate-900 border border-slate-800 rounded-xl p-1">
              <button
                type="button"
                onClick={handleOpenProjector}
                title="Traer la ventana del proyector al frente"
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500/25 transition"
              >
                <Monitor className="w-3.5 h-3.5" />
                Proyector Activo
              </button>
              <button
                type="button"
                onClick={handleToggleProjectorFullscreen}
                title="Alternar pantalla completa en la ventana del proyector"
                className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold transition ${
                  projectorFullscreen
                    ? "bg-amber-500 text-slate-950"
                    : "text-slate-300 hover:bg-slate-800"
                }`}
              >
                <Maximize2 className="w-3.5 h-3.5" />
                {projectorFullscreen ? "Salir Fullscreen" : "Pantalla Completa"}
              </button>
              <button
                type="button"
                onClick={handleHideProjector}
                title="Cerrar/Ocultar temporalmente la ventana del proyector"
                className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-rose-300 hover:bg-rose-500/10 transition"
              >
                <MonitorOff className="w-3.5 h-3.5" />
                Ocultar
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={handleOpenProjector}
              className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold bg-amber-500 hover:bg-amber-400 text-slate-950 shadow-lg shadow-amber-500/20 animate-pulse transition"
            >
              <ExternalLink className="w-4 h-4" />
              Abrir Ventana Proyector (Rhema Live)
            </button>
          )}

          {/* Interruptor Modo Automático vs Modo Operador */}
          <div className="flex items-center bg-slate-900 border border-slate-800 rounded-xl p-1">
            <button
              type="button"
              onClick={() => setAutoMode(true)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                autoMode
                  ? "bg-amber-500 text-slate-950 shadow"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <Zap className="w-3.5 h-3.5" />
              Modo Automático
            </button>
            <button
              type="button"
              onClick={() => setAutoMode(false)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                !autoMode
                  ? "bg-indigo-500 text-white shadow"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              Modo Operador
            </button>
          </div>

          {/* Selector de Micrófono (Laptop vs Behringer USB) */}
          <AudioSelector
            devices={audioDevices}
            selectedDeviceId={selectedDeviceId}
            audioLevel={audioLevel}
            onSelectDevice={changeAudioDevice}
            onRefreshDevices={refreshAudioDevices}
            isConnected={isConnected}
          />
        </div>
      </header>

      {/* Contenido Principal */}
      <main className="flex-1 p-6 grid grid-cols-1 lg:grid-cols-12 gap-6 max-w-[1600px] w-full mx-auto">
        {/* Columna Izquierda (7 cols): Monitor de Voz + Tarjeta Previa (Modo Operador) + Cola */}
        <div className="lg:col-span-7 flex flex-col gap-5">
          <LiveTranscript partialText={partialText} isConnected={isConnected} />

          {/* Tarjeta Previa de Aprobación cuando está activo el Modo Operador */}
          {!autoMode && (
            <div
              className={`rounded-2xl p-4 border transition-all ${
                pendingVerse
                  ? "bg-indigo-950/40 border-indigo-500/60 shadow-lg shadow-indigo-950/50"
                  : "bg-slate-900/40 border-slate-800/80"
              }`}
            >
              <div className="flex items-center justify-between gap-2 mb-2">
                <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-indigo-300">
                  <Sparkles className="w-4 h-4 text-indigo-400" />
                  <span>
                    Modo Operador · Vista Previa para Aprobar (Barra Espaciadora)
                  </span>
                </div>
                {pendingVerse && (
                  <button
                    type="button"
                    onClick={dismissPendingVerse}
                    className="text-xs text-slate-400 hover:text-rose-300 inline-flex items-center gap-1"
                  >
                    <X className="w-3.5 h-3.5" />
                    Descartar
                  </button>
                )}
              </div>

              {pendingVerse ? (
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-950/80 border border-indigo-500/30 rounded-xl p-3.5">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-base font-bold text-amber-400">
                        {pendingVerse.reference}
                      </span>
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300">
                        PENDIENTE DE APROBACIÓN
                      </span>
                    </div>
                    <p className="text-sm text-slate-200 leading-relaxed">
                      “{pendingVerse.text}”
                    </p>
                  </div>

                  <button
                    type="button"
                    onClick={() => projectVerse(pendingVerse)}
                    className="shrink-0 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs px-4 py-2.5 rounded-xl shadow flex items-center gap-2 transition"
                  >
                    <Check className="w-4 h-4 stroke-[2.5]" />
                    Aprobar y Proyectar [Espacio]
                  </button>
                </div>
              ) : (
                <p className="text-xs text-slate-400">
                  El Modo Operador está activo: cuando la IA detecte una cita bíblica, aparecerá aquí para que la apruebes antes de salir al proyector.
                </p>
              )}
            </div>
          )}

          <div className="flex-1">
            <VerseQueue
              queue={detectedQueue}
              activeVerse={activeVerse}
              autoMode={autoMode}
              onProjectVerse={projectVerse}
            />
          </div>
        </div>

        {/* Columna Derecha (5 cols): Monitor de Proyección en Vivo + Buscador Manual */}
        <div className="lg:col-span-5 flex flex-col gap-5">
          {/* Tarjeta de Vista Previa de Rhema Live (Proyector) */}
          <div className="bg-slate-900/70 border border-slate-800/90 rounded-2xl p-4 shadow-lg">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Monitor
                  className={`w-4 h-4 ${
                    projectorOpen ? "text-emerald-400" : "text-slate-500"
                  }`}
                />
                <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-200">
                  Salida en Vivo (Rhema Live)
                </h2>
              </div>

              <div className="flex items-center gap-2">
                {!projectorOpen && (
                  <button
                    type="button"
                    onClick={handleOpenProjector}
                    className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-lg bg-amber-500 text-slate-950 hover:bg-amber-400 transition"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    Abrir Proyector
                  </button>
                )}

                {activeVerse && (
                  <button
                    onClick={clearProjection}
                    className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-lg bg-rose-500/15 text-rose-300 border border-rose-500/30 hover:bg-rose-500/25 transition"
                  >
                    <EyeOff className="w-3.5 h-3.5" />
                    Limpiar Texto
                  </button>
                )}
              </div>
            </div>

            <div className="aspect-video rounded-xl bg-gradient-to-br from-slate-950 via-[#080d1a] to-black border border-slate-800 p-6 flex flex-col items-center justify-center text-center relative overflow-hidden">
              {activeVerse ? (
                <>
                  <p className="font-serif text-base md:text-lg text-slate-100 leading-relaxed line-clamp-5">
                    “{activeVerse.text}”
                  </p>
                  <div className="mt-4 flex items-center gap-2">
                    <span className="text-sm font-bold text-amber-400 uppercase tracking-wide">
                      {activeVerse.reference}
                    </span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 font-semibold">
                      {activeVerse.version}
                    </span>
                  </div>
                </>
              ) : (
                <p className="text-xs uppercase tracking-[0.2em] text-slate-600">
                  Pantalla en negro · Sin versículo activo
                </p>
              )}
            </div>

            {/* Controles rápidos de navegación: Versículo Anterior / Siguiente */}
            <div className="mt-3 flex items-center justify-between gap-2">
              <button
                type="button"
                disabled={!activeVerse}
                onClick={() => stepAdjacentVerse(-1)}
                className="flex-1 inline-flex items-center justify-center gap-1.5 text-xs font-semibold py-2 px-3 rounded-xl bg-slate-950 border border-slate-800 text-slate-300 hover:border-amber-500/40 hover:text-amber-300 disabled:opacity-40 transition"
              >
                <ChevronLeft className="w-4 h-4" />
                Versículo Anterior [←]
              </button>
              <button
                type="button"
                disabled={!activeVerse}
                onClick={() => stepAdjacentVerse(1)}
                className="flex-1 inline-flex items-center justify-center gap-1.5 text-xs font-semibold py-2 px-3 rounded-xl bg-slate-950 border border-slate-800 text-slate-300 hover:border-amber-500/40 hover:text-amber-300 disabled:opacity-40 transition"
              >
                Siguiente Versículo [→]
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Buscador Manual Rápido */}
          <div className="bg-slate-900/70 border border-slate-800/90 rounded-2xl p-4 flex-1 flex flex-col">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Search className="w-4 h-4 text-amber-400" />
                <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-200">
                  Buscador Manual Rápido
                </h2>
              </div>
              <span className="text-[11px] text-slate-400">
                Cita, rango (8:4-9) o frase · Enter para proyectar
              </span>
            </div>

            <form onSubmit={handleManualSearchSubmit} className="flex gap-2 mb-3">
              <input
                type="text"
                value={manualQuery}
                onChange={(e) => {
                  setManualQuery(e.target.value);
                  searchVerses(e.target.value);
                }}
                placeholder="Ej: Génesis 8:4-9, Juan 3:16 o 'Dios es amor'..."
                className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs md:text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-amber-500/60"
              />
              <button
                type="submit"
                className="bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold text-xs px-4 py-2 rounded-xl transition flex items-center gap-1.5"
              >
                <Search className="w-3.5 h-3.5" />
                Buscar
              </button>
            </form>

            <div className="space-y-2 overflow-y-auto max-h-[240px] pr-1">
              {searchResults.map((res) => {
                const isProjected = activeVerse?.reference === res.reference;
                return (
                  <div
                    key={`search-${res.reference}`}
                    className={`rounded-xl p-2.5 flex items-start justify-between gap-3 border transition ${
                      isProjected
                        ? "bg-amber-500/10 border-amber-500/40"
                        : "bg-slate-950/80 border-slate-800/80 hover:border-slate-700"
                    }`}
                  >
                    <div className="min-w-0">
                      <span className="text-xs font-bold text-amber-400">
                        {res.reference}
                      </span>
                      <p className="text-xs text-slate-300 line-clamp-2 mt-0.5">
                        {res.text}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => projectVerse(res)}
                      className="shrink-0 bg-slate-800 hover:bg-amber-500 hover:text-slate-950 text-slate-200 text-xs font-semibold px-2.5 py-1.5 rounded-lg transition flex items-center gap-1"
                    >
                      <Send className="w-3 h-3" />
                      Proyectar
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};
