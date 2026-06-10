import type { Metadata } from "next";

const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL ||
  "https://minjikim89.github.io/make-me-unicorn";

export const metadata: Metadata = {
  title: "Make Me Unicorn — SaaS Launch Readiness Checklist",
  description:
    "670+ checklist items across 15 categories. Catch what AI-generated code misses before it costs you users, money, or trust.",
  openGraph: {
    title: "Make Me Unicorn",
    description: "The open-source launch checklist for solo SaaS builders.",
    type: "website",
    url: SITE_URL,
    siteName: "Make Me Unicorn",
    // TODO: Add OG image once brand assets are finalized
    // images: [{ url: `${SITE_URL}/og.png`, width: 1200, height: 630 }],
  },
  twitter: {
    card: "summary_large_image",
    title: "Make Me Unicorn",
    description: "670+ SaaS launch checklist items. Stop building blind.",
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
