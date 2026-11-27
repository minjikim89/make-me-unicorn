import Link from "next/link";

export default function Home() {
  return (
    <main>
      <h1>Invoicely</h1>
      <p>Send invoices, get paid.</p>
      <Link href="/login">Sign in</Link>
    </main>
  );
}
