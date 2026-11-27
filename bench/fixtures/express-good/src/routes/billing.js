import { Router } from "express";
import { db } from "../db.js";
import { verifyStripeEvent } from "../stripe.js";

export const billingRouter = Router();

billingRouter.post("/webhook", async (req, res) => {
  const event = verifyStripeEvent(req);
  if (!event) return res.status(400).send("bad signature");
  const seen = await db.query("INSERT INTO stripe_events (id) VALUES ($1) ON CONFLICT DO NOTHING", [event.id]);
  if (seen.rowCount === 0) return res.sendStatus(200);
  if (event.type === "invoice.paid") {
    await db.query("UPDATE accounts SET plan = 'pro' WHERE stripe_customer_id = $1", [event.data.object.customer]);
  }
  res.sendStatus(200);
});
