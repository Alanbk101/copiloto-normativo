import type { Source } from "@/lib/types";

interface Props {
  source: Source;
  index: number;
}

export default function SourceCard({ source, index }: Props) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Fuente {index + 1}
          </p>
          <p className="mt-0.5 break-words font-medium text-slate-800">
            {source.structure_path}
          </p>
        </div>
        <span className="shrink-0 rounded-md bg-indigo-100 px-2.5 py-1 text-xs font-semibold text-indigo-700">
          Pág. {source.page_number}
        </span>
      </div>
    </div>
  );
}
