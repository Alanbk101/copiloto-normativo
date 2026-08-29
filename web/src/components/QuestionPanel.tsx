"use client";

import { useState } from "react";
import { askQuestion } from "@/lib/api";
import type { AskResponse } from "@/lib/types";
import AnswerDisplay from "./AnswerDisplay";

export default function QuestionPanel() {
  const [question, setQuestion] = useState("");
  const [isAsking, setIsAsking] = useState(false);
  const [result, setResult] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (!question.trim() || isAsking) return;

    setIsAsking(true);
    setResult(null);
    setError(null);

    try {
      const data = await askQuestion(question.trim());
      setResult(data);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Error al consultar. Intenta de nuevo.",
      );
    } finally {
      setIsAsking(false);
    }
  }

  return (
    <div className="space-y-4">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void submit();
        }}
        className="space-y-3"
      >
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
              e.preventDefault();
              void submit();
            }
          }}
          placeholder="¿Qué dice el artículo sobre las obligaciones del contribuyente?"
          rows={3}
          disabled={isAsking}
          className="w-full resize-none rounded-lg border border-slate-300 px-4 py-3 text-sm text-slate-800 placeholder-slate-400 shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-200 disabled:cursor-not-allowed disabled:opacity-60"
        />
        <div className="flex items-center justify-between">
          <p className="text-xs text-slate-400">Ctrl+Enter para enviar</p>
          <button
            type="submit"
            disabled={isAsking || !question.trim()}
            className="rounded-lg bg-indigo-600 px-5 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Preguntar
          </button>
        </div>
      </form>

      {isAsking && (
        <div className="flex items-start gap-3 rounded-lg border border-blue-200 bg-blue-50 px-5 py-4">
          <svg
            className="mt-0.5 h-5 w-5 shrink-0 animate-spin text-blue-500"
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
          <div>
            <p className="font-semibold text-blue-800">
              Analizando los documentos…
            </p>
            <p className="mt-0.5 text-sm text-blue-600">
              El modelo corre en CPU local. La primera consulta puede tardar
              hasta 2 minutos.
            </p>
          </div>
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-5 py-4">
          <p className="font-semibold text-red-800">Error en la consulta</p>
          <p className="mt-1 text-sm text-red-700">{error}</p>
        </div>
      )}

      {result && !isAsking && <AnswerDisplay result={result} />}
    </div>
  );
}
