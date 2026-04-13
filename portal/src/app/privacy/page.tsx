import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Privacy — Nikita",
  description: "How Nikita handles your information.",
};

export default function PrivacyPage() {
  return (
    <main className="mx-auto max-w-2xl px-6 py-16">
      <h1 className="text-3xl font-semibold tracking-tight">Privacy</h1>
      <p className="mt-6 text-muted-foreground">
        Nikita collects only what&apos;s needed to play the game: your profile
        answers, your phone number (used exclusively for her calls — never
        shared, never sold, never used for marketing), and your conversation
        history. The full privacy policy is still being drafted.
      </p>
      <p className="mt-4 text-muted-foreground">
        Questions? Email{" "}
        <a href="mailto:support@nikita.example" className="underline">
          support@nikita.example
        </a>
        .
      </p>
      <Link
        href="/onboarding"
        className="mt-8 inline-block text-sm underline"
      >
        ← Back to onboarding
      </Link>
    </main>
  );
}
