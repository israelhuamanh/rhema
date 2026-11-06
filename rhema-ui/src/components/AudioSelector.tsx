import React from "react";
import { Mic, Radio, RefreshCw } from "lucide-react";
import type { AudioDevice } from "../types/rhema";

interface AudioSelectorProps {
  devices: AudioDevice[];
  selectedDeviceId: number | null;
  audioLevel: number;
  onSelectDevice: (deviceId: number) => void;
  onRefreshDevices: () => void;
  isConnected: boolean;
}

export const AudioSelector: React.FC<AudioSelectorProps> = ({
  devices,
  selectedDeviceId,
  audioLevel,
  onSelectDevice,
  onRefreshDevices,
  isConnected,
}) => {
  return (
    <div className="flex items-center gap-2.5 bg-slate-900/90 border border-slate-800 rounded-xl px-3.5 py-2">
      <div className="flex items-center gap-2 text-xs font-medium text-slate-400">
        <Mic
          className={`w-4 h-4 transition-colors ${
            audioLevel > 12 ? "text-emerald-400" : "text-amber-400"
          }`}
        />
        <span>Micrófono Único:</span>
      </div>

      <select
        value={selectedDeviceId ?? ""}
        onChange={(e) => {
          const val = Number(e.target.value);
          if (!Number.isNaN(val)) {
            onSelectDevice(val);
          }
        }}
        disabled={!isConnected || devices.length === 0}
        className="bg-slate-950 text-slate-100 text-xs font-medium rounded-lg px-3 py-1.5 border border-slate-800 focus:outline-none focus:border-amber-500/60 disabled:opacity-50 min-w-[240px]"
      >
        {devices.length === 0 ? (
          <option value="">Detectando micrófonos...</option>
        ) : (
          devices.map((dev) => {
            const isUsbInterface =
              /behringer|usb|codec|line|interfaz/i.test(dev.name);
            return (
              <option key={dev.id} value={dev.id}>
                [{dev.id}] {isUsbInterface ? "🎚️ " : "🎙️ "}
                {dev.name}
              </option>
            );
          })
        )}
      </select>

      {/* Vúmetro en tiempo real (indicador de nivel de voz del micrófono elegido) */}
      <div
        title={`Nivel de entrada de voz: ${audioLevel}%`}
        className="w-16 h-2.5 bg-slate-950 border border-slate-800 rounded-full overflow-hidden flex items-center p-0.5"
      >
        <div
          className={`h-full rounded-full transition-all duration-150 ${
            audioLevel > 75
              ? "bg-amber-400"
              : audioLevel > 10
              ? "bg-emerald-400"
              : "bg-slate-700"
          }`}
          style={{ width: `${Math.max(6, Math.min(100, audioLevel))}%` }}
        />
      </div>

      <button
        type="button"
        onClick={onRefreshDevices}
        disabled={!isConnected}
        title="Actualizar lista de micrófonos (si conectaste o desconectaste un micrófono USB / Bluetooth)"
        className="p-1.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-400 hover:text-amber-400 hover:border-amber-500/40 transition disabled:opacity-40"
      >
        <RefreshCw className="w-3.5 h-3.5" />
      </button>

      <div className="flex items-center gap-1.5 pl-2 border-l border-slate-800">
        <Radio
          className={`w-3.5 h-3.5 ${
            isConnected ? "text-emerald-400 animate-pulse" : "text-rose-500"
          }`}
        />
        <span
          className={`text-[11px] font-semibold uppercase tracking-wider ${
            isConnected ? "text-emerald-400" : "text-rose-400"
          }`}
        >
          {isConnected ? "Motor Online" : "Reconectando"}
        </span>
      </div>
    </div>
  );
};
