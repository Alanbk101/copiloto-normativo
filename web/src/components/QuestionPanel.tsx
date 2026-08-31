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
    <div className="space-y-6">
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
          rows={4}
          disabled={isAsking}
          className="w-full resize-none border border-linea bg-papel px-4 py-3 text-sm text-tinta placeholder-masa/50 transition-colors focus:border-guinda focus:outline-none focus:ring-1 focus:ring-guinda/20 disabled:cursor-not-allowed disabled:opacity-60"
        />
        <div className="flex items-center justify-between">
          <p className="text-xs text-masa/70">Ctrl+Enter para enviar</p>
          <button
            type="submit"
            disabled={isAsking || !question.trim()}
            className="border border-guinda bg-guinda px-5 py-2 text-sm font-medium text-papel transition-colors hover:bg-papel hover:text-guinda focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-guinda focus-visible:ring-offset-2 focus-visible:ring-offset-papel disabled:cursor-not-allowed disabled:opacity-50"
          >
            Preguntar
          </button>
        </div>
      </form>

      {isAsking && (
        <div className="border-l-2 border-l-masa pl-4 py-1">
          <p className="text-sm font-medium text-tinta">
            Analizando los documentos…
          </p>
          <p className="mt-0.5 text-xs text-masa">
            El modelo corre en CPU local. La primera consulta puede tardar hasta
            2 minutos.
          </p>
        </div>
      )}

      {error && (
        <div className="border-l-2 border-l-red-700 pl-4 py-1">
          <p className="text-sm font-medium text-red-800">
            Error en la consulta
          </p>
          <p className="mt-0.5 text-xs text-red-700">{error}</p>
        </div>
      )}

      {result && !isAsking && <AnswerDisplay result={result} />}
    </div>
  );
}
