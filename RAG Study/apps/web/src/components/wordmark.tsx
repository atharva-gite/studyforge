import Link from "next/link";

export function Wordmark({ href = "/" }: { href?: string }) {
  return (
    <Link href={href} className="inline-flex items-center gap-2 font-display text-xl tracking-tight text-bone">
      <span className="inline-block h-2.5 w-2.5 bg-ember" aria-hidden="true" />
      StudyForge
    </Link>
  );
}
