# RHEMA - Especificación de Arquitectura y Reglas para el Agente (Antigravity)

> **DIRECTIVA PRINCIPAL PARA EL AGENTE DE IA (ANTIGRAVITY):** 
> Actúa como un Arquitecto de Software Senior e Ingeniero Full-Stack (Python + Rust/Tauri v2 + React/TypeScript). Este archivo es tu fuente única de verdad (*Single Source of Truth*). Antes de escribir código, crear archivos o ejecutar comandos en la terminal, valida que tus acciones cumplan estrictamente con las restricciones y la estructura definidas en este documento.

---

## 1. Identidad y Visión del Proyecto

* **Nombre del Proyecto:** Rhema (del griego *ῥῆμα*: la palabra hablada en el momento preciso).
* **Repositorio:** `rhema` (Monorepo).
* **Identificador de Aplicación (Bundle ID):** `com.rhema.app`
* **Propósito:** Sistema de escritorio nativo, 100% local, escalable y de ultra-baja latencia para iglesias. Captura la voz del predicador en tiempo real (vía micrófono local o interfaz de audio USB Behringer), transcribe el audio offline, extrae citas bíblicas mediante NLP/Regex, las consulta en SQLite local y las proyecta automáticamente en una pantalla extendida.

---

## 2. Reglas Inquebrantables para el Agente (Hard Constraints)

1. **100% Offline y Local:** Prohibido usar APIs externas de pago o en la nube (nada de OpenAI Whisper API, Google Cloud STT ni Web Scraping). Todo el procesamiento ocurre en la máquina local.
2. **Aplicación de Escritorio Nativa (NO Web Browser):** La interfaz visual se construye sobre **Tauri v2**. Nunca abras ventanas en Chrome/Edge; todo debe renderizarse dentro de las ventanas nativas del ejecutable de Tauri.
3. **Eficiencia de Recursos:** Optimizado para correr fluidamente con un consumo mínimo de RAM y CPU. La latencia total (voz a pantalla) debe ser `< 1.5 segundos`.
4. **Arquitectura Escalable y Desacoplada:** El motor de voz/IA (`rhema-engine`) y la interfaz gráfica (`rhema-ui`) son módulos independientes que se comunican mediante un protocolo de eventos WebSocket local (`ws://127.0.0.1:8765/ws`). Esto permitirá en el futuro agregar módulos nuevos (letras de canciones, anuncios, control móvil en red local) sin reescribir el núcleo.
5. **Gestión de Ventanas (Multi-Monitor):** Tauri v2 debe gestionar dos ventanas nativas:
   * `main` (**Rhema Studio**): Panel de control para el operador en la pantalla de la laptop.
   * `projector` (**Rhema Live**): Ventana sin bordes (`decorations: false`), siempre visible (`alwaysOnTop: true`) y en pantalla completa enviada al monitor secundario/proyector.

---

## 3. Stack Tecnológico Oficial

### Módulo 1: `rhema-engine` (Backend & AI Engine - Python 3.10+)
* **Captura de Audio:** `sounddevice` (lectura de stream de audio por bloques en subproceso sin bloqueo, permitiendo seleccionar el dispositivo de entrada por ID).
* **Reconocimiento de Voz (STT):** `vosk` utilizando el modelo en español ligero `vosk-model-small-es-0.42`.
* **Procesamiento de Texto (NLP/Regex):** `re` y `unicodedata` nativos. Incluye un normalizador de números hablados a dígitos y un diccionario de sinónimos de libros bíblicos.
* **Base de Datos:** `sqlite3` nativo consultando `biblia_rv1960.db` en modo solo lectura para máxima velocidad.
* **Servidor de Eventos:** `fastapi` + `uvicorn` + `websockets` sirviendo en el puerto `8765`.

### Módulo 2: `rhema-ui` (Desktop App - Tauri v2 + React)
* **Core Nativo:** **Tauri v2** (Rust).
* **Frontend:** React 18 + Vite + TypeScript.
* **Estilos:** Tailwind CSS (Diseño oscuro moderno para el panel de control; tipografía de alto contraste y lectura limpia para el proyector).
* **Iconografía:** `lucide-react`.

---

## 4. Estructura del Monorepo (`rhema/`)

El agente debe crear, mantener y respetar estrictamente este árbol de directorios:

```text
rhema/
├── .gitignore                   # Ignorar venv/, __pycache__/, node_modules/, target/, models/
├── README.md                    # Documentación general
├── arquitectura_proyector_biblico.md  # Este archivo de especificación
│
├── rhema-engine/                # [PYTHON] Motor de IA, Audio y Base de Datos
│   ├── venv/                    # Entorno virtual de Python (No subir a Git)
│   ├── models/                  # Modelos Vosk descargados (ej. vosk-model-small-es-0.42)
│   ├── database/
│   │   ├── biblia_rv1960.db     # Base de datos SQLite compilada
│   │   └── seed.py              # Script para poblar/crear la BD si no existe
│   ├── src/
│   │   ├── __init__.py
│   │   ├── config.py            # Variables de configuración (Puerto, rutas, audio chunk)
│   │   ├── audio_stream.py      # Listado de micrófonos y captura con sounddevice
│   │   ├── stt_engine.py        # Wrapper del reconocedor Vosk
│   │   ├── verse_extractor.py   # Conversor texto->número, normalizador de libros y Regex
│   │   ├── db_manager.py        # Consultas indexadas a SQLite
│   │   └── main.py              # Punto de entrada: Servidor FastAPI + WebSocket + Loop de Audio
│   └── requirements.txt
│
└── rhema-ui/                    # [TAURI v2 + REACT] Aplicación de Escritorio
    ├── src/
    │   ├── windows/
    │   │   ├── StudioWindow.tsx     # Panel de Control (operador en laptop)
    │   │   └── ProjectorWindow.tsx  # Pantalla de proyección limpia (iglesia)
    │   ├── components/
    │   │   ├── AudioSelector.tsx    # Selector de micrófono (Laptop vs Behringer)
    │   │   ├── LiveTranscript.tsx   # Monitor en tiempo real de lo que escucha la IA
    │   │   └── VerseQueue.tsx       # Cola de versículos detectados (Modo Auto / Manual)
    │   ├── hooks/
    │   │   └── useRhemaSocket.ts    # Hook de conexión y reconexión automática al WebSocket
    │   ├── types/
    │   │   └── rhema.d.ts           # Interfaces TypeScript del contrato JSON
    │   ├── App.tsx                  # Enrutador según el label de la ventana de Tauri
    │   └── main.tsx
    ├── src-tauri/
    │   ├── tauri.conf.json          # Configuración de ventanas 'main' y 'projector'
    │   ├── capabilities/            # Permisos de ventana y monitores en Tauri v2
    │   └── src/
    │       └── main.rs
    ├── package.json
    └── tailwind.config.js
```

---

## 5. Esquema de Base de Datos y Contrato de Eventos (API Interna)

### A. Esquema SQLite (`rhema-engine/database/biblia_rv1960.db`)
```sql
CREATE TABLE IF NOT EXISTS versiculos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    libro_id INTEGER NOT NULL,
    libro_nombre TEXT NOT NULL, -- Nombre normalizado: 'Mateo', '1 Juan', 'Salmos'
    capitulo INTEGER NOT NULL,
    versiculo INTEGER NOT NULL,
    texto TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_busqueda_rapida 
ON versiculos(libro_nombre, capitulo, versiculo);
```

### B. Protocolo WebSocket (`ws://127.0.0.1:8765/ws`)
Comunicación bidireccional en formato JSON para asegurar escalabilidad:

**Eventos emitidos por `rhema-engine` (Python ➔ Tauri):**
1. `TRANSCRIPTION_PARTIAL`: Texto mientras el pastor sigue hablando.
   ```json
   { "event": "TRANSCRIPTION_PARTIAL", "payload": { "text": "vamos a leer en mateo capítulo siete" } }
   ```
2. `VERSE_DETECTED`: Cita identificada y extraída de SQLite con éxito.
   ```json
   {
     "event": "VERSE_DETECTED",
     "payload": {
       "reference": "Mateo 7:8",
       "book": "Mateo",
       "chapter": 7,
       "verse": 8,
       "text": "Porque todo aquel que pide, recibe; y el que busca, halla; y al que llama, se le abrirá.",
       "version": "RVR1960",
       "timestamp": 1710000000
     }
   }
   ```
3. `AUDIO_DEVICES_LIST`: Lista de micrófonos detectados en Windows.
   ```json
   {
     "event": "AUDIO_DEVICES_LIST",
     "payload": [
       { "id": 1, "name": "Micrófono integrado (Realtek Audio)" },
       { "id": 2, "name": "Línea de entrada (Behringer USB Audio)" }
     ]
   }
   ```

**Comandos recibidos por `rhema-engine` (Tauri ➔ Python):**
1. `CHANGE_AUDIO_DEVICE`: Cambiar en caliente entre el micrófono de la laptop y la interfaz Behringer.
   ```json
   { "command": "CHANGE_AUDIO_DEVICE", "payload": { "device_id": 2 } }
   ```

---

## 6. Especificación del Algoritmo de Extracción (`verse_extractor.py`)

El motor de lenguaje natural basado en reglas debe procesar el texto de Vosk en 3 pasos secuenciales:

1. **Sanitización y Conversión Numérica:**
   * Eliminar tildes para uniformidad (`"capítulo"` ➔ `"capitulo"`, `"génesis"` ➔ `"genesis"`).
   * Transformar números escritos con palabras en español a dígitos (`"uno"` ➔ `1`, `"veintitres"` ➔ `23`, `"ciento diecinueve"` ➔ `119`).
2. **Mapeo de Sinónimos Bíblicos:**
   * Normalizar prefijos ordinales: `"primera de"`, `"primero de"`, `"1 de"` ➔ `"1 "`.
   * Normalizar variaciones: `"salmo"` ➔ `"Salmos"`, `"apocalipsis"` ➔ `"Apocalipsis"`, `"san mateo"` ➔ `"Mateo"`.
3. **Evaluación de Patrones Regex:**
   * **Patrón 1 (Estándar):** `\b(?P<libro>[1-3]?\s?[a-z]+)\s+(?:capitulo\s+)?(?P<capitulo>\d+)\s+(?:versiculo|verso|al)\s+(?P<versiculo>\d+)\b`
     *(Ejemplo: "mateo 7 versiculo 8" o "1 juan capitulo 4 verso 8")*.
   * **Patrón 2 (Invertido):** `\bcapitulo\s+(?P<capitulo>\d+)\s+de\s+(?P<libro>[1-3]?\s?[a-z]+)\s+(?:versiculo|verso)\s+(?P<versiculo>\d+)\b`
     *(Ejemplo: "capitulo 7 de mateo versiculo 8")*.

---

## 7. Hoja de Ruta de Ejecución para Antigravity (Paso a Paso)

**INSTRUCCIÓN DE FLUJO DE TRABAJO:** Ejecuta una sola fase a la vez. No pases a la siguiente fase hasta que el usuario confirme que la prueba de la fase actual funciona en su máquina.

### 🔹 FASE 1: Prototipo de Consola y Captura de Micrófono (`rhema-engine` Core)
1. Crear la estructura de carpetas de `rhema-engine/` y el archivo `.gitignore`.
2. Generar `requirements.txt` (`vosk`, `sounddevice`, `fastapi`, `uvicorn`, `websockets`).
3. Implementar `verse_extractor.py` con soporte completo para los 66 libros de la Biblia y conversión de números en texto a dígitos (del 1 al 150). Crear un script de test unitario rápido para validar que frases como *"hermanos leamos primera de juan capítulo cuatro versículo ocho"* devuelvan `('1 Juan', 4, 8)`.
4. Implementar `audio_stream.py` y `stt_engine.py` para escuchar el micrófono por defecto de la laptop e imprimir las detecciones en la terminal.

### 🔹 FASE 2: Base de Datos SQLite y Servidor WebSocket
1. Crear `db_manager.py` y un script `seed.py` que genere `biblia_rv1960.db` (inicialmente con datos de prueba o descargando el JSON abierto de la RVR1960 para poblar los 31,102 versículos).
2. Crear `main.py` integrando FastAPI + WebSockets con el bucle de captura de audio en segundo plano (`asyncio`).

### 🔹 FASE 3: Aplicación de Escritorio Multi-Ventana (`rhema-ui`)
1. Inicializar Tauri v2 con React, TypeScript y Tailwind CSS dentro de `rhema-ui/`.
2. Configurar `tauri.conf.json` para levantar las dos ventanas (`StudioWindow` y `ProjectorWindow`).
3. Conectar `useRhemaSocket.ts` al backend de Python y mostrar los versículos en pantalla completa con transiciones suaves.

### 🔹 FASE 4: Controles de Producción en Vivo
1. Añadir selector de micrófono en `StudioWindow` (para alternar entre Laptop e interfaz Behringer).
2. Añadir interruptor de **"Modo Automático"** (proyecta al instante) vs **"Modo Operador"** (muestra el versículo detectado en una tarjeta previa para aprobarlo con un clic o barra espaciadora).
3. Añadir buscador manual rápido por si el pastor pide un versículo sin decir la cita completa.
