const STAGES = [
  { key: "UPLOADED", label: "Upload" },
  { key: "EXTRACTING", label: "Extract" },
  { key: "CHUNKING", label: "Chunk" },
  { key: "EMBEDDING", label: "Embed" },
  { key: "INDEXING", label: "Index" },
  { key: "READY", label: "Ready" },
] as const;

function stageIndex(status: string): number {
  if (status === "PROCESSING") return 1;
  const index = STAGES.findIndex((stage) => stage.key === status);
  return index === -1 ? 0 : index;
}

export function StageTracker({ status }: { status: string }) {
  const failed = status === "FAILED";
  const current = stageIndex(status);

  return (
    <ol className="flex flex-wrap gap-x-3 gap-y-2" aria-label="Ingestion pipeline">
      {STAGES.map((stage, index) => {
        const done = !failed && index < current;
        const active = !failed && index === current;
        const mark = failed ? "border border-fault bg-transparent" : done || active ? "bg-ember" : "border border-line bg-transparent";
        const text = failed ? "text-fault" : active ? "text-bone" : done ? "text-slag" : "text-slag/70";
        return (
          <li key={stage.key} className="flex items-center gap-1.5">
            <span className={`inline-block h-1.5 w-1.5 ${mark}`} aria-hidden="true" />
            <span className={`font-mono text-[10px] uppercase tracking-[0.14em] ${text}`}>{stage.label}</span>
          </li>
        );
      })}
    </ol>
  );
}
