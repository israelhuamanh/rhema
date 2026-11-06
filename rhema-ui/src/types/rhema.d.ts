export interface VersePayload {
  reference: string;
  book: string;
  chapter: number;
  verse: number;
  verse_end?: number;
  text: string;
  version: string;
  timestamp: number;
}

export interface AudioDevice {
  id: number;
  name: string;
}

export interface TranscriptionPartialPayload {
  text: string;
}

export type RhemaServerEvent =
  | { event: "TRANSCRIPTION_PARTIAL"; payload: TranscriptionPartialPayload }
  | { event: "VERSE_DETECTED"; payload: VersePayload }
  | { event: "VERSE_PROJECTED"; payload: VersePayload }
  | { event: "PROJECTION_CLEARED"; payload: Record<string, never> }
  | { event: "AUDIO_DEVICES_LIST"; payload: AudioDevice[] }
  | { event: "AUDIO_DEVICE_CHANGED"; payload: { device_id: number | null } }
  | { event: "AUDIO_LEVEL"; payload: { level: number; device_id: number | null } }
  | { event: "SEARCH_RESULTS"; payload: VersePayload[] };

export type RhemaClientCommand =
  | { command: "CHANGE_AUDIO_DEVICE"; payload: { device_id: number } }
  | { command: "REQUEST_AUDIO_DEVICES"; payload?: Record<string, never> }
  | { command: "PROJECT_VERSE"; payload: { verse: VersePayload } }
  | { command: "ADJACENT_VERSE"; payload: { step: number } }
  | { command: "CLEAR_PROJECTION"; payload?: Record<string, never> }
  | { command: "SEARCH_VERSES"; payload: { query: string } };
