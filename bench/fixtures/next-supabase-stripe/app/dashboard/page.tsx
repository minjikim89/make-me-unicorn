import { AdminPanel } from "@/components/AdminPanel";
import { InvoiceNote } from "@/components/InvoiceNote";

export default function Dashboard() {
  return (
    <main>
      <h1>Dashboard</h1>
      <InvoiceNote html="<b>Welcome back</b>" />
      <AdminPanel />
    </main>
  );
}
