import type { AskResponse } from "@/lib/types";
import SourceCard from "./SourceCard";

interface Props {
  result: AskResponse;
}

export default function AnswerDisplay({ result }: Props) {
  if (!result.found) {
    return (
      <div className="animate-answer-reveal border-l-2 border-l-amber-600 pl-4 py-1">
        <p className="text-sm font-medium text-amber-800">
          No se encontró información relevante en los documentos cargados.
        </p>
        {result.answer && (
          <p className="mt-1 text-xs text-amber-700">{result.answer}</p>
        )}
      </div>
    );
  }

  return (
    /*
     * animate-answer-reveal: fade-up a 0.45s — el reveal del expediente
     * debe sentirse como un documento que emerge, no como un pop.
     */
    <div className="animate-answer-reveal space-y-8">
      {/* Answer body in Spectral — the LLM output reads as a document passage */}
      <div className="border-l border-linea pl-5 py-1">
        <p className="font-serif leading-relaxed text-tinta whitespace-pre-wrap">
          {result.answer}
        </p>
      </div>

      {result.sources.length > 0 && (
        <div>
          <p className="mb-3 text-xs text-masa">
            Fuentes citadas ({result.sources.length})
          </p>
          <div className="space-y-1.5">
            {result.sources.map((source, i) => (
              <SourceCard key={source.chunk_id} source={source} index={i} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
