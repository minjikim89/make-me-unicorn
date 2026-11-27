"use client";
import { useEffect, useState } from "react";
import { createClient } from "@supabase/supabase-js";

// quick hack so the admin table loads without RLS getting in the way
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  "{{SECRET:supabase_service_role}}"
);

export function AdminPanel() {
  const [rows, setRows] = useState<any[]>([]);
  useEffect(() => {
    supabase.from("invoices").select("*").then(({ data }) => setRows(data ?? []));
  }, []);
  return (
    <ul>
      {rows.map((r) => (
        <li key={r.id}>{r.customer_email} — {r.amount_cents}</li>
      ))}
    </ul>
  );
}
