import type { AskResponse, Document } from "./types";

// The browser calls /api/* on the same origin (localhost:3000).
// next.config.ts rewrites those requests to the backend over the internal
// Docker network — no CORS headers needed, no NEXT_PUBLIC_ env var required.
const API_BASE = "/api";

export async function uploadDocument(file: File): Promise<Document> {
  const body = new FormData();
  body.append("file", file);

  const res = await fetch(`${API_BASE}/documents`, { method: "POST", body });
  if (!res.ok) {
    throw new Error(`Error al subir el documento (${res.status})`);
  }
  return res.json() as Promise<Document>;
}

export async function getDocument(id: string): Promise<Document> {
  const res = await fetch(`${API_BASE}/documents/${id}`);
  if (!res.ok) {
    throw new Error(`Error al obtener el documento (${res.status})`);
  }
  return res.json() as Promise<Document>;
}

export async function askQuestion(question: string): Promise<AskResponse> {
  const controller = new AbortController();
  // The LLM runs on CPU — first inference can take up to 2 minutes.
  const timeoutId = setTimeout(() => controller.abort(), 180_000);

  try {
    const res = await fetch(`${API_BASE}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
      signal: controller.signal,
    });

    if (!res.ok) {
      throw new Error(`Error del servidor (${res.status})`);
    }
    return res.json() as Promise<AskResponse>;
  } catch (err) {
    if (err instanceof Error && err.name === "AbortError") {
      throw new Error("La consulta tardó demasiado. Intenta de nuevo.");
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }
}
