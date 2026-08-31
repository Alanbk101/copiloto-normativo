import type { Source } from "@/lib/types";

interface Props {
  source: Source;
  index: number;
}

export default function SourceCard({ source, index }: Props) {
  return (
    /*
     * Staggered fade-up per source so the list of citations arrives
     * sequentially rather than all at once.
     */
    <div
      className="flex animate-fade-up bg-cita border-l-2 border-l-guinda"
      style={{ animationDelay: `${index * 80}ms` }}
    >
      {/* Citation number — the guinda left border + this number together
          evoke the indentation of a numbered article in the DOF */}
      <div className="flex shrink-0 items-start px-4 py-3">
        <span className="tabular-nums text-sm font-semibold text-guinda">
          {index + 1}
        </span>
      </div>

      {/* Structure path + page number in leader-dot style (table of contents) */}
      <div className="min-w-0 flex-1 py-3 pr-4">
        <div className="flex items-baseline gap-2">
          <span className="truncate text-sm font-medium text-tinta">
            {source.structure_path}
          </span>
          {/* Leader dots between path and page number */}
          <span className="mb-[3px] min-w-[16px] flex-1 border-b border-dashed border-linea" />
          <span className="shrink-0 tabular-nums text-xs text-masa">
            Pág.&nbsp;{source.page_number}
          </span>
        </div>
      </div>
    </div>
  );
}
