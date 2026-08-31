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
    <main className="min-h-screen px-6 py-12 sm:px-10 lg:px-16">
      <div className="mx-auto max-w-5xl">
        <header className="mb-10">
          <h1 className="font-serif text-3xl font-semibold tracking-tight text-tinta">
            Copiloto Normativo
          </h1>
          <p className="mt-2 text-sm text-masa">
            Sistema de consulta · Documentos regulatorios · México
          </p>
          <hr className="mt-8 border-linea" />
        </header>

        {/*
         * Two-column layout on lg+: §1 Expediente (left) | §2 Consulta (right)
         * Stacks to single column on smaller screens: §1 on top, §2 below.
         */}
        <div className="grid grid-cols-1 divide-y divide-[#D8D4CC] lg:grid-cols-[2fr_3fr] lg:divide-y-0">
          {/* §1 Expediente */}
          <section className="pb-12 lg:pb-0 lg:pr-12">
            <h2 className="mb-6 text-sm font-medium text-masa">
              <span className="font-semibold text-guinda">§1</span> Expediente
            </h2>
            <DocumentUploader onUploaded={handleUploaded} />
            {documents.length > 0 && (
              <div className="mt-6">
                <DocumentList documents={documents} />
              </div>
            )}
          </section>

          {/* §2 Consulta — border-l is the vertical rule between columns */}
          <section className="pt-12 lg:border-l lg:border-[#D8D4CC] lg:pl-12 lg:pt-0">
            <h2 className="mb-6 text-sm font-medium text-masa">
              <span className="font-semibold text-guinda">§2</span> Consulta
            </h2>
            <QuestionPanel />
          </section>
        </div>
      </div>
    </main>
  );
}
