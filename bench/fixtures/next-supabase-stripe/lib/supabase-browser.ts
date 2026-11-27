"use client";
import { createBrowserClient } from "@supabase/ssr";

// Browser client: anon key only. Safe to expose.
export function getBrowserClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );
}
