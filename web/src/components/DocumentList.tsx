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
  pending: "bg-slate-100 text-slate-600",
  processing: "bg-blue-100 text-blue-700",
  completed: "bg-emerald-100 text-emerald-700",
  failed: "bg-red-100 text-red-700",
};

function InlineSpinner() {
  return (
    <svg
      className="h-3.5 w-3.5 animate-spin text-blue-500"
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
    <ul className="space-y-2">
      {documents.map((doc) => {
        const isActive =
          doc.status === "pending" || doc.status === "processing";

        return (
          <li
            key={doc.id}
            className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white px-4 py-3"
          >
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-slate-800">
                {doc.filename}
              </p>
              {doc.status === "completed" && doc.chunk_count > 0 && (
                <p className="mt-0.5 text-xs text-slate-400">
                  {doc.chunk_count} fragmentos indexados
                </p>
              )}
            </div>
            <div className="flex shrink-0 items-center gap-2">
              {isActive && <InlineSpinner />}
              <span
                className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${STATUS_CLASSES[doc.status]}`}
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
