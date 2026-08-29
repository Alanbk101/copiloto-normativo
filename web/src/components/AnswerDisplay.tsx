import type { AskResponse } from "@/lib/types";
import SourceCard from "./SourceCard";

interface Props {
  result: AskResponse;
}

export default function AnswerDisplay({ result }: Props) {
  if (!result.found) {
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 px-5 py-4">
        <p className="text-sm font-semibold text-amber-800">
          No se encontró información relevante en los documentos cargados.
        </p>
        {result.answer && (
          <p className="mt-1 text-sm text-amber-700">{result.answer}</p>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-slate-200 bg-white px-5 py-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
          Respuesta
        </p>
        <p className="whitespace-pre-wrap leading-relaxed text-slate-800">
          {result.answer}
        </p>
      </div>

      {result.sources.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
            Fuentes citadas ({result.sources.length})
          </p>
          <div className="space-y-2">
            {result.sources.map((source, i) => (
              <SourceCard key={source.chunk_id} source={source} index={i} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
