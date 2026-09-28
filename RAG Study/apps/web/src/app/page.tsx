import Link from "next/link";

export default function HomePage() {
  return (
    <main className="mx-auto flex max-w-3xl flex-col px-6 py-20">
      <p className="text-xs font-medium tracking-[0.22em] text-pine uppercase">Course study desk</p>
      <h1 className="mt-4 max-w-2xl font-serif text-5xl leading-[1.05] text-ink sm:text-6xl">
        You have the material. The next question is what to study.
      </h1>
      <p className="mt-6 max-w-xl text-lg leading-relaxed text-muted">
        Folio starts with the course itself. Create one, upload the syllabus and lectures, and the
        rest of the study system has a source of truth to work from.
      </p>
      <div className="mt-10 flex flex-wrap gap-3">
        <Link
          href="/register"
          className="rounded-full bg-pine px-5 py-2.5 text-sm text-sand hover:bg-pine-deep"
        >
          Create an account
        </Link>
        <Link
          href="/login"
          className="rounded-full border border-line bg-sand px-5 py-2.5 text-sm text-ink hover:border-ink"
        >
          Sign in
        </Link>
      </div>
    </main>
  );
}
