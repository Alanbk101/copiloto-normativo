"use client";

import { useEffect, useState } from "react";
import { getDocument } from "@/lib/api";
import type { Document } from "@/lib/types";
import DocumentUploader from "@/components/DocumentUploader";
import DocumentList from "@/components/DocumentList";
import QuestionPanel from "@/components/QuestionPanel";

const TERMINAL = new Set(["completed", "failed"]);

export default function HomePage() {
  const [documents, setDocuments] = useState<Document[]>([]);

  // A stable string that changes only when the set of in-progress IDs changes.
  // Using it as the effect dependency avoids restarting the interval on every
  // poll tick while still reacting when a document completes or a new one appears.
  const pendingDocIds = documents
    .filter((d) => !TERMINAL.has(d.status))
    .map((d) => d.id)
    .join(",");

  useEffect(() => {
    if (!pendingDocIds) return;

    const ids = pendingDocIds.split(",");

    const interval = setInterval(async () => {
      const results = await Promise.allSettled(ids.map(getDocument));
      setDocuments((prev) =>
        prev.map((doc) => {
          const i = ids.indexOf(doc.id);
          if (i === -1) return doc;
          const result = results[i];
          return result.status === "fulfilled" ? result.value : doc;
        }),
      );
    }, 2500);

    return () => clearInterval(interval);
  }, [pendingDocIds]);

  function handleUploaded(doc: Document) {
    setDocuments((prev) => [doc, ...prev]);
  }

  return (
    <main className="mx-auto max-w-3xl space-y-6 px-4 py-10">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">
          Copiloto Normativo
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Sube documentos regulatorios y consulta su contenido en lenguaje
          natural.
        </p>
      </header>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-xs font-semibold uppercase tracking-wide text-slate-400">
          Documentos
        </h2>
        <DocumentUploader onUploaded={handleUploaded} />
        {documents.length > 0 && (
          <div className="mt-4">
            <DocumentList documents={documents} />
          </div>
        )}
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-xs font-semibold uppercase tracking-wide text-slate-400">
          Consulta
        </h2>
        <QuestionPanel />
      </section>
    </main>
  );
}
