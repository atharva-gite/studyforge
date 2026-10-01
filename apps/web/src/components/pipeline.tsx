const STAGES = [
  { name: "Upload", detail: "Files land in the course corpus.", live: true },
  { name: "Extract", detail: "Pages become text.", live: true },
  { name: "Chunk", detail: "Text is split on document structure.", live: true },
  { name: "Embed", detail: "Chunks enter the vector index.", live: true },
  { name: "Retrieve", detail: "Hybrid search returns evidence.", live: true },
  { name: "Cite", detail: "Answers point at chunk ids.", live: true },
];

export function Pipeline() {
  return (
    <div>
      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-ember">Ingestion</p>
      <h2 className="mt-3 font-display text-3xl text-bone">From PDF to cited evidence</h2>
      <ol className="mt-8">
        {STAGES.map((stage, index) => (
          <li key={stage.name} className="grid grid-cols-[auto_1fr] gap-4 border-t border-line py-4">
            <span className="pt-1 font-mono text-xs text-slag">{String(index + 1).padStart(2, "0")}</span>
            <div>
              <div className="flex flex-wrap items-center gap-3">
                <span className={`inline-block h-2 w-2 ${stage.live ? "bg-ember" : "border border-slag"}`} aria-hidden="true" />
                <span className="font-display text-lg">{stage.name}</span>
                <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-slag">
                  {stage.live ? "Live" : "Later forge stage"}
                </span>
              </div>
              <p className="mt-1 text-sm text-slag">{stage.detail}</p>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
