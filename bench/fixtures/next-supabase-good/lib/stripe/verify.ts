import Stripe from "stripe";

export const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!);

// The route handler delegates verification to this helper.
export function parseStripeEvent(rawBody: string, signature: string | null): Stripe.Event | null {
  if (!signature) return null;
  try {
    return stripe.webhooks.constructEvent(rawBody, signature, process.env.STRIPE_WEBHOOK_SECRET!);
  } catch {
    return null;
  }
}
