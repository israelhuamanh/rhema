import React, { useEffect, useState } from "react";
import { getCurrentWebviewWindow } from "@tauri-apps/api/webviewWindow";
import { ProjectorWindow } from "./windows/ProjectorWindow";
import { StudioWindow } from "./windows/StudioWindow";

export const App: React.FC = () => {
  const [windowLabel, setWindowLabel] = useState<string>(() => {
    try {
      const params = new URLSearchParams(window.location.search);
      const paramLabel = params.get("window");
      if (paramLabel) return paramLabel;
      return getCurrentWebviewWindow().label;
    } catch {
      return "main";
    }
  });

  useEffect(() => {
    try {
      const label = getCurrentWebviewWindow().label;
      if (label) {
        setWindowLabel(label);
      }
    } catch {
      // Fallback para entorno fuera de Tauri
    }
  }, []);

  if (windowLabel === "projector") {
    return <ProjectorWindow />;
  }

  return <StudioWindow />;
};

export default App;
