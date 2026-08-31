import type { Document, DocumentStatus } from "@/lib/types";

interface Props {
  documents: Document[];
}

const STATUS_LABEL: Record<DocumentStatus, string> = {
  pending: "En cola",
  processing: "Procesando",
  completed: "Listo",
  failed: "Error",
};

const STATUS_CLASSES: Record<DocumentStatus, string> = {
  pending: "text-masa bg-linea/60",
  processing: "text-masa bg-linea/60",
  completed: "text-guinda bg-guinda/10",
  failed: "text-red-700 bg-red-50",
};

function InlineSpinner() {
  return (
    <svg
      className="h-3.5 w-3.5 animate-spin text-guinda"
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
  );
}

export default function DocumentList({ documents }: Props) {
  return (
    <ul className="divide-y divide-linea">
      {documents.map((doc) => {
        const isActive =
          doc.status === "pending" || doc.status === "processing";

        return (
          <li
            key={doc.id}
            className="flex items-center justify-between gap-3 py-3"
          >
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-tinta">
                {doc.filename}
              </p>
              {doc.status === "completed" && doc.chunk_count > 0 && (
                <p className="mt-0.5 text-xs text-masa">
                  {doc.chunk_count} fragmentos indexados
                </p>
              )}
            </div>
            <div className="flex shrink-0 items-center gap-2">
              {isActive && <InlineSpinner />}
              <span
                className={`px-2 py-0.5 text-xs font-medium ${STATUS_CLASSES[doc.status]}`}
              >
                {STATUS_LABEL[doc.status]}
              </span>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
