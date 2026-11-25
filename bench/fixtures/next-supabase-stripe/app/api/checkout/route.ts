import { NextResponse } from "next/server";
import { z } from "zod";
import { stripe } from "@/lib/stripe";
import { rateLimit } from "@/lib/rate-limit";

const Body = z.object({ invoiceId: z.string().uuid(), amountCents: z.number().int().positive() });

export async function POST(req: Request) {
  const ip = req.headers.get("x-forwarded-for") ?? "unknown";
  if (!rateLimit(`checkout:${ip}`, 5)) {
    return NextResponse.json({ error: "too many requests" }, { status: 429 });
  }
  const parsed = Body.safeParse(await req.json());
  if (!parsed.success) return NextResponse.json({ error: "bad request" }, { status: 400 });

  const session = await stripe.checkout.sessions.create({
    mode: "payment",
    line_items: [{ price_data: { currency: "usd", product_data: { name: "Invoice" }, unit_amount: parsed.data.amountCents }, quantity: 1 }],
    success_url: `${process.env.NEXT_PUBLIC_APP_URL}/dashboard?paid=1`,
    cancel_url: `${process.env.NEXT_PUBLIC_APP_URL}/dashboard`,
    metadata: { invoiceId: parsed.data.invoiceId },
  });
  return NextResponse.json({ url: session.url });
}
