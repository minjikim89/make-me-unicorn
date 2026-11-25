export const metadata = { title: "Ledgerly", description: "Invoices for small teams" };

const jsonLd = { "@context": "https://schema.org", "@type": "SoftwareApplication", name: "Ledgerly" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
        {children}
      </body>
    </html>
  );
}
