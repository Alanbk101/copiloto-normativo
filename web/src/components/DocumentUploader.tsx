"use client";

import { useRef, useState } from "react";
import { uploadDocument } from "@/lib/api";
import type { Document } from "@/lib/types";

interface Props {
  onUploaded: (doc: Document) => void;
}

export default function DocumentUploader({ onUploaded }: Props) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFile(file: File) {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("Solo se aceptan archivos PDF.");
      return;
    }
    setError(null);
    setIsUploading(true);
    try {
      const doc = await uploadDocument(file);
      onUploaded(doc);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Error al subir el archivo.",
      );
    } finally {
      setIsUploading(false);
    }
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) void handleFile(file);
  }

  function onInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) void handleFile(file);
    e.target.value = "";
  }

  const zoneClass = [
    "flex cursor-pointer flex-col items-center justify-center px-6 py-10 transition-colors select-none",
    isDragging
      ? "border-2 border-guinda bg-guinda/[0.06]"
      : "border border-linea hover:border-guinda/50 hover:bg-guinda/[0.025]",
    isUploading ? "cursor-not-allowed opacity-60" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div>
      <div
        role="button"
        tabIndex={0}
        onClick={() => !isUploading && inputRef.current?.click()}
        onKeyDown={(e) =>
          e.key === "Enter" && !isUploading && inputRef.current?.click()
        }
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={onDrop}
        className={zoneClass}
      >
        {isUploading ? (
          <p className="text-sm text-masa">Subiendo…</p>
        ) : (
          <>
            {/*
             * Ícono de documento normativo — folio con esquina doblada y
             * tres líneas de texto (artículos del expediente).
             * SVG inline sin dependencias de librerías.
             * Transiciona de masa/50 a guinda en drag-over.
             */}
            <svg
              className={`mb-3 h-8 w-8 transition-colors duration-150 ${
                isDragging ? "text-guinda" : "text-masa/50"
              }`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.25}
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <line x1="10" y1="9" x2="8" y2="9" />
            </svg>

            <p className="text-sm text-tinta">Deposite el expediente</p>
            <p className="mt-1.5 text-xs text-masa">
              o{" "}
              <span className="text-guinda underline underline-offset-2">
                haga clic para seleccionar
              </span>
            </p>
            <p className="mt-3 text-xs text-masa/50">Solo archivos .pdf</p>
          </>
        )}
      </div>

      <input
        ref={inputRef}
        type="file"
        accept=".pdf"
        className="hidden"
        onChange={onInputChange}
      />

      {error && (
        <p className="mt-2 border-l-2 border-l-red-700 pl-3 text-sm text-red-700">
          {error}
        </p>
      )}
    </div>
  );
}
