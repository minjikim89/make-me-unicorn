import { createClient } from "@/lib/supabase/server";
// Passwordless only: magic link + Google OAuth. There are no passwords in this app.
export async function signInWithMagicLink(email: string) {
  const supabase = await createClient();
  return supabase.auth.signInWithOtp({ email });
}
export async function signInWithGoogle() {
  const supabase = await createClient();
  return supabase.auth.signInWithOAuth({ provider: "google" });
}
