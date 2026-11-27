"use client";
import Link from "next/link";
import { useState } from "react";
import { getBrowserClient } from "@/lib/supabase/browser";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const { error } = await getBrowserClient().auth.signInWithPassword({ email, password });
    if (!error) window.location.href = "/dashboard";
  }

  return (
    <form onSubmit={onSubmit}>
      <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
      <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
      <button type="submit">Sign in</button>
      <Link href="/forgot-password">Forgot your password?</Link>
    </form>
  );
}
