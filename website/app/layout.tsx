import type { Metadata } from "next";

const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL ||
  "https://minjikim89.github.io/make-me-unicorn";

export const metadata: Metadata = {
  title: "make-me-unicorn: a launch gate for AI coding agents",
  description:
    "Blocks your AI coding agent's git commit when it ships an unverified webhook, a Supabase table without RLS, or a leaked key. Deterministic, offline, no LLM.",
  openGraph: {
    title: "make-me-unicorn",
    description: "A launch gate for AI coding agents.",
    type: "website",
    url: SITE_URL,
    siteName: "Make Me Unicorn",
    // TODO: Add OG image once brand assets are finalized
    // images: [{ url: `${SITE_URL}/og.png`, width: 1200, height: 630 }],
  },
  twitter: {
    card: "summary_large_image",
    title: "make-me-unicorn",
    description: "Blocks your AI coding agent's git commit when it ships an unverified webhook, a Supabase table without RLS, or a leaked key. Deterministic, offline, no LLM.",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
