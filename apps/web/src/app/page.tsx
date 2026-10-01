import Link from "next/link";

import { Pipeline } from "@/components/pipeline";
import { buttonClass } from "@/components/ui";
import { Wordmark } from "@/components/wordmark";

export default function HomePage() {
  return (
    <main className="grid min-h-screen lg:grid-cols-2">
      <section className="flex flex-col justify-center px-6 py-16 sm:px-10 lg:px-16">
        <Wordmark />
        <p className="mt-12 font-mono text-[11px] uppercase tracking-[0.18em] text-ember">Course corpus</p>
        <h1 className="mt-4 max-w-xl font-display text-5xl leading-[1.02] text-bone sm:text-6xl">
          Grounded answers from the material you upload.
        </h1>
        <p className="mt-6 max-w-md text-lg leading-relaxed text-slag">
          StudyForge keeps each course as its own corpus. Upload the syllabus and lectures. Questions stay locked
          until those files are chunked, embedded, and cited from retrieved evidence.
        </p>
        <div className="mt-10 flex flex-wrap gap-3">
          <Link href="/register" className={buttonClass}>
            Create an account
          </Link>
          <Link href="/login" className="border border-line px-4 py-2.5 text-sm text-bone hover:border-bone">
            Sign in
          </Link>
        </div>
      </section>
      <section className="border-t border-line bg-panel px-6 py-14 sm:px-10 lg:border-t-0 lg:border-l lg:px-12 lg:py-16">
        <Pipeline />
      </section>
    </main>
  );
}
