import { NextResponse } from "next/server";
import { parseStripeEvent } from "@/lib/stripe/verify";
import { supabaseAdmin } from "@/lib/supabase/admin";

export async function POST(req: Request) {
  const event = parseStripeEvent(await req.text(), req.headers.get("stripe-signature"));
  if (!event) return NextResponse.json({ error: "invalid signature" }, { status: 400 });

  // at-most-once: the event id is the primary key
  const { error } = await supabaseAdmin.from("stripe_events").insert({ id: event.id });
  if (error?.code === "23505") return NextResponse.json({ received: true, duplicate: true });

  if (event.type === "checkout.session.completed") {
    await supabaseAdmin.from("invoices").update({ status: "paid" }).eq("stripe_session_id", event.data.object.id);
  }
  return NextResponse.json({ received: true });
}
