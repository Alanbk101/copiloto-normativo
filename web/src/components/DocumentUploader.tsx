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
    // Reset so the same file can be selected again after a failed upload.
    e.target.value = "";
  }

  const zoneClass = [
    "flex cursor-pointer flex-col items-center justify-center border px-6 py-10 transition-colors select-none",
    isDragging ? "border-guinda bg-guinda/5" : "border-linea hover:border-masa",
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
            <p className="text-sm text-tinta">Arrastre el PDF aquí</p>
            <p className="mt-1.5 text-xs text-masa">
              o{" "}
              <span className="text-guinda underline underline-offset-2">
                haga clic para seleccionar
              </span>
            </p>
            <p className="mt-3 text-xs text-masa/60">Solo archivos .pdf</p>
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
