"use client";

import { useEffect, useState } from "react";
import { getDocument } from "@/lib/api";
import type { Document } from "@/lib/types";
import DocumentUploader from "@/components/DocumentUploader";
import DocumentList from "@/components/DocumentList";
import QuestionPanel from "@/components/QuestionPanel";

const TERMINAL = new Set(["completed", "failed"]);

/* Separador gradiente reutilizable — guinda → linea → transparente */
function GradientRule({ className = "" }: { className?: string }) {
  return (
    <div
      className={`h-px ${className}`}
      style={{
        background:
          "linear-gradient(to right, rgba(110,20,35,0.4), #D8D4CC 38%, transparent)",
      }}
    />
  );
}

export default function HomePage() {
  const [documents, setDocuments] = useState<Document[]>([]);

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
      {/*
       * Contenedor principal con tinte guinda al 2 % (punto 1).
       * Diferencia el área de contenido del cuerpo de página alrededor.
       * El papel + líneas del body se ven "debajo" gracias a la
       * semi-transparencia — el contenido flota sobre la textura.
       */}
      <div
        className="mx-auto max-w-5xl"
        style={{ backgroundColor: "rgba(110,20,35,0.02)" }}
      >
        {/*
         * Header con posición relativa para el § decorativo de esquina (punto 4).
         */}
        <header className="relative mb-10">
          {/*
           * § pequeño en esquina superior derecha — contrapeso visual al
           * border-l-4 guinda de la izquierda. Guinda al 20 %: visible,
           * legible como decorativo, nunca compite con el título.
           */}
          <span
            aria-hidden="true"
            className="pointer-events-none absolute right-0 top-0 select-none font-serif font-semibold leading-none"
            style={{ fontSize: "1.5rem", color: "rgba(110,20,35,0.2)" }}
          >
            §
          </span>

          <div className="border-l-4 border-guinda pl-4">
            <h1 className="font-serif text-4xl font-semibold tracking-tight text-tinta">
              Copiloto Normativo
            </h1>
            <p className="mt-2 text-sm text-masa">
              Sistema de consulta{" "}
              <span className="font-medium text-guinda">·</span>{" "}
              Documentos regulatorios{" "}
              <span className="font-medium text-guinda">·</span>{" "}
              México
            </p>
          </div>

          <GradientRule className="mt-8" />
        </header>

        {/*
         * Grid de columnas. Cada section lleva un fondo ligeramente más
         * oscuro que el contenedor (punto 5) — crea profundidad de capas:
         * body (paper) → container (guinda 2%) → columnas (tinta 3%).
         */}
        <div className="grid grid-cols-1 divide-y divide-[#D8D4CC] lg:grid-cols-[2fr_3fr] lg:divide-y-0">
          {/* §1 Expediente */}
          <section
            className="pb-12 lg:pb-0 lg:pr-12"
            style={{ backgroundColor: "rgba(17,17,16,0.03)" }}
          >
            <h2 className="mb-6 flex items-center gap-2 text-sm font-medium text-masa">
              <span className="inline-block bg-guinda px-1.5 py-px font-sans text-xs font-semibold text-papel">
                §1
              </span>
              Expediente
            </h2>
            <DocumentUploader onUploaded={handleUploaded} />
            {documents.length > 0 && (
              <div className="mt-6">
                <DocumentList documents={documents} />
              </div>
            )}
          </section>

          {/* §2 Consulta */}
          <section
            className="pt-12 lg:border-l lg:border-[#D8D4CC] lg:pl-12 lg:pt-0"
            style={{ backgroundColor: "rgba(17,17,16,0.03)" }}
          >
            <h2 className="mb-6 flex items-center gap-2 text-sm font-medium text-masa">
              <span className="inline-block bg-guinda px-1.5 py-px font-sans text-xs font-semibold text-papel">
                §2
              </span>
              Consulta
            </h2>
            <QuestionPanel />
          </section>
        </div>

        {/*
         * Footer técnico (punto 2).
         * Mismo separador gradiente que el header — consistencia editorial.
         * Stack técnico en masa/70 — comunica solidez técnica sin
         * competir con el contenido principal.
         */}
        <footer className="mt-16 pb-2">
          <GradientRule />
          <p className="mt-5 text-center text-xs text-masa/70">
            FastAPI{" "}
            <span className="mx-1 text-guinda">·</span>
            PostgreSQL + pgvector{" "}
            <span className="mx-1 text-guinda">·</span>
            Next.js 15{" "}
            <span className="mx-1 text-guinda">·</span>
            Groq{" "}
            <span className="mx-1 text-guinda">·</span>
            Jina AI
          </p>
        </footer>
      </div>
    </main>
  );
}
