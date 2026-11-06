import type { VersePayload } from "../types/rhema";

export const DEMO_VERSES: VersePayload[] = [
  {
    reference: "Juan 3:16",
    book: "Juan",
    chapter: 3,
    verse: 16,
    text: "Porque de tal manera amó Dios al mundo, que ha dado a su Hijo unigénito, para que todo aquel que en él cree, no se pierda, mas tenga vida eterna.",
    version: "RVR1960",
    timestamp: Date.now(),
  },
  {
    reference: "Salmos 23:1",
    book: "Salmos",
    chapter: 23,
    verse: 1,
    text: "Jehová es mi pastor; nada me faltará.",
    version: "RVR1960",
    timestamp: Date.now(),
  },
  {
    reference: "Filipenses 4:13",
    book: "Filipenses",
    chapter: 4,
    verse: 13,
    text: "Todo lo puedo en Cristo que me fortalece.",
    version: "RVR1960",
    timestamp: Date.now(),
  },
  {
    reference: "Génesis 1:1",
    book: "Génesis",
    chapter: 1,
    verse: 1,
    text: "En el principio creó Dios los cielos y la tierra.",
    version: "RVR1960",
    timestamp: Date.now(),
  },
  {
    reference: "Romanos 8:28",
    book: "Romanos",
    chapter: 8,
    verse: 28,
    text: "Y sabemos que a los que aman a Dios, todas las cosas les ayudan a bien, esto es, a los que conforme a su propósito son llamados.",
    version: "RVR1960",
    timestamp: Date.now(),
  },
  {
    reference: "Salmos 119:105",
    book: "Salmos",
    chapter: 119,
    verse: 105,
    text: "Lámpara es a mis pies tu palabra, Y lumbrera a mi camino.",
    version: "RVR1960",
    timestamp: Date.now(),
  },
  {
    reference: "Mateo 7:7",
    book: "Mateo",
    chapter: 7,
    verse: 7,
    text: "Pedid, y se os dará; buscad, y hallaréis; llamad, y se os abrirá.",
    version: "RVR1960",
    timestamp: Date.now(),
  },
  {
    reference: "Isaías 40:31",
    book: "Isaías",
    chapter: 40,
    verse: 31,
    text: "pero los que esperan a Jehová tendrán nuevas fuerzas; levantarán alas como las águilas; correrán, y no se cansarán; caminarán, y no se fatigarán.",
    version: "RVR1960",
    timestamp: Date.now(),
  },
  {
    reference: "Proverbios 3:5-6",
    book: "Proverbios",
    chapter: 3,
    verse: 5,
    verse_end: 6,
    text: "Fíate de Jehová de todo tu corazón, Y no te apoyes en tu propia prudencia. Reconócelo en todos tus caminos, Y él enderezará tus veredas.",
    version: "RVR1960",
    timestamp: Date.now(),
  },
  {
    reference: "Jeremías 29:11",
    book: "Jeremías",
    chapter: 29,
    verse: 11,
    text: "Porque yo sé los pensamientos que tengo acerca de vosotros, dice Jehová, pensamientos de paz, y no de mal, para daros el fin que esperáis.",
    version: "RVR1960",
    timestamp: Date.now(),
  },
  {
    reference: "Josué 1:9",
    book: "Josué",
    chapter: 1,
    verse: 9,
    text: "Mira que te mando que te esfuerces y seas valiente; no temas ni desmayes, porque Jehová tu Dios estará contigo en dondequiera que vayas.",
    version: "RVR1960",
    timestamp: Date.now(),
  },
  {
    reference: "1 Juan 4:8",
    book: "1 Juan",
    chapter: 4,
    verse: 8,
    text: "El que no ama, no ha conocido a Dios; porque Dios es amor.",
    version: "RVR1960",
    timestamp: Date.now(),
  },
  {
    reference: "Salmos 91:1-2",
    book: "Salmos",
    chapter: 91,
    verse: 1,
    verse_end: 2,
    text: "El que habita al abrigo del Altísimo Morará bajo la sombra del Omnipotente. Diré yo a Jehová: Esperanza mía, y castillo mío; Mi Dios, en quien confiaré.",
    version: "RVR1960",
    timestamp: Date.now(),
  },
  {
    reference: "Mateo 28:19",
    book: "Mateo",
    chapter: 28,
    verse: 19,
    text: "Por tanto, id, y doctrinad a todos los gentiles, bautizándolos en el nombre del Padre, y del Hijo, y del Espíritu Santo.",
    version: "RVR1960",
    timestamp: Date.now(),
  },
  {
    reference: "1 Corintios 13:4",
    book: "1 Corintios",
    chapter: 13,
    verse: 4,
    text: "El amor es sufrido, es benigno; el amor no tiene envidia, el amor no es jactancioso, no se envanece.",
    version: "RVR1960",
    timestamp: Date.now(),
  },
];

export function searchDemoVerses(query: string): VersePayload[] {
  if (!query || !query.trim()) return [];
  const normalizedQuery = query.toLowerCase().trim();

  return DEMO_VERSES.filter((v) => {
    const matchRef = v.reference.toLowerCase().includes(normalizedQuery);
    const matchBook = v.book.toLowerCase().includes(normalizedQuery);
    const matchText = v.text.toLowerCase().includes(normalizedQuery);
    return matchRef || matchBook || matchText;
  });
}

// Extractor básico para demo de voz en navegador
export function matchSpokenVerseInDemo(spokenText: string): VersePayload | null {
  const norm = spokenText
    .toLowerCase()
    .replace(/[.,;:!?]/g, "")
    .replace(/\buno\b/g, "1")
    .replace(/\bdos\b/g, "2")
    .replace(/\btres\b/g, "3")
    .replace(/\bcuatro\b/g, "4")
    .replace(/\bcinco\b/g, "5")
    .replace(/\bseis\b/g, "6")
    .replace(/\bsiete\b/g, "7")
    .replace(/\bocho\b/g, "8")
    .replace(/\bnueve\b/g, "9")
    .replace(/\bdiez\b/g, "10")
    .replace(/\bonce\b/g, "11")
    .replace(/\bdoce\b/g, "12")
    .replace(/\btrece\b/g, "13")
    .replace(/\bcatorce\b/g, "14")
    .replace(/\bquince\b/g, "15")
    .replace(/\bdieciseis\b|\bdiecis\u00e9is\b/g, "16")
    .replace(/\bveinte\b/g, "20")
    .replace(/\bveintitres\b|\bveintitr\u00e9s\b/g, "23")
    .replace(/\bveintiocho\b/g, "28")
    .replace(/\bveintinueve\b/g, "29")
    .replace(/\btreinta\b/g, "30")
    .replace(/\btreinta y uno\b/g, "31")
    .replace(/\bcuarenta\b/g, "40")
    .replace(/\bnoventa y uno\b/g, "91")
    .replace(/\bciento diecinueve\b/g, "119")
    .replace(/\bciento cinco\b/g, "105")
    .replace(/\bprimera\b|\bprimero\b|\bprimer\b/g, "1")
    .replace(/\bsegunda\b|\bsegundo\b/g, "2")
    .replace(/\bsan\b|\bsanto\b/g, "");

  for (const item of DEMO_VERSES) {
    const bookNorm = item.book.toLowerCase();
    const hasBook = norm.includes(bookNorm);
    const hasChapter = norm.includes(item.chapter.toString());
    const hasVerse = norm.includes(item.verse.toString());

    if (hasBook && hasChapter && hasVerse) {
      return { ...item, timestamp: Date.now() };
    }
  }

  // Fallback: búsqueda por palabras clave significativas
  if (norm.includes("pastor") && norm.includes("nada me faltará")) {
    return { ...DEMO_VERSES[1], timestamp: Date.now() };
  }
  if (norm.includes("de tal manera amó dios")) {
    return { ...DEMO_VERSES[0], timestamp: Date.now() };
  }
  if (norm.includes("todo lo puedo en cristo")) {
    return { ...DEMO_VERSES[2], timestamp: Date.now() };
  }
  if (norm.includes("principio creó dios")) {
    return { ...DEMO_VERSES[3], timestamp: Date.now() };
  }

  return null;
}
