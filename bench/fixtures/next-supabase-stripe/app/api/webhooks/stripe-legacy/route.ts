import { NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabase-admin";

// old endpoint, still registered in the Stripe dashboard
export async function POST(req: Request) {
  const event = await req.json();

  if (event.type === "invoice.paid") {
    await supabaseAdmin
      .from("subscriptions")
      .update({ status: "active" })
      .eq("stripe_customer_id", event.data.object.customer);
  }
  return NextResponse.json({ received: true });
}
