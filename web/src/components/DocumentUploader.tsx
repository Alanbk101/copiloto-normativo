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
    "flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-10 transition-colors select-none",
    isDragging
      ? "border-indigo-400 bg-indigo-50"
      : "border-slate-300 bg-slate-50 hover:border-indigo-300 hover:bg-indigo-50/40",
    isUploading ? "cursor-not-allowed opacity-60" : "",
  ].join(" ");

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
          <>
            <svg
              className="h-6 w-6 animate-spin text-indigo-500"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
            <p className="mt-2 text-sm text-slate-600">Subiendo…</p>
          </>
        ) : (
          <>
            <svg
              className="h-8 w-8 text-slate-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M12 16V4m0 0L8 8m4-4 4 4M6 20h12"
              />
            </svg>
            <p className="mt-2 text-sm font-medium text-slate-700">
              Arrastra un PDF aquí o{" "}
              <span className="text-indigo-600 underline underline-offset-2">
                selecciona uno
              </span>
            </p>
            <p className="mt-1 text-xs text-slate-500">Solo archivos .pdf</p>
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

      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </div>
  );
}
