"use client";
import { useState } from "react";
import { getBrowserClient } from "@/lib/supabase/browser";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    await getBrowserClient().auth.resetPasswordForEmail(email, { redirectTo: `${window.location.origin}/update-password` });
    setSent(true);
  }

  return sent ? <p>Check your inbox.</p> : (
    <form onSubmit={onSubmit}>
      <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
      <button type="submit">Send reset link</button>
    </form>
  );
}
