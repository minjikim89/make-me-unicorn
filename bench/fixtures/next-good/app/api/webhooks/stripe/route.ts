import Stripe from "stripe";
import { headers } from "next/headers";
import { db } from "@/lib/db";
import { stripeEvents } from "@/lib/schema";

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!);

export async function POST(req: Request) {
  const body = await req.text();
  const sig = (await headers()).get("Stripe-Signature")!;
  let event: Stripe.Event;
  try {
    event = await stripe.webhooks.constructEventAsync(body, sig, process.env.STRIPE_WEBHOOK_SECRET!);
  } catch {
    return new Response("bad signature", { status: 400 });
  }
  // dedupe: insert the Stripe event id, skip if we've already seen it
  const inserted = await db.insert(stripeEvents).values({ id: event.id }).onConflictDoNothing().returning();
  if (inserted.length === 0) return new Response("duplicate", { status: 200 });
  return new Response("ok");
}
