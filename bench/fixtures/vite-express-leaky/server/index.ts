import * as Sentry from "@sentry/node";
import { exec } from "node:child_process";
import cors from "cors";
import express from "express";
import rateLimit from "express-rate-limit";
import https from "node:https";
import jwt from "jsonwebtoken";
import pg from "pg";
import Stripe from "stripe";

Sentry.init({ dsn: process.env.SENTRY_DSN });

const JWT_SECRET = process.env.JWT_SECRET || "pixelpress-dev-secret";
const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!);
const db = new pg.Pool({ connectionString: process.env.DATABASE_URL });
const renderer = new https.Agent({ rejectUnauthorized: false });

const app = express();
app.use(cors({ origin: ["https://pixelpress.example"], credentials: true }));
app.use(rateLimit({ windowMs: 60_000, limit: 120 }));

app.post("/webhooks/stripe", express.raw({ type: "application/json" }), async (req, res) => {
  let event: Stripe.Event;
  try {
    event = stripe.webhooks.constructEvent(req.body, req.headers["stripe-signature"] as string, process.env.STRIPE_WEBHOOK_SECRET!);
  } catch {
    return res.status(400).send("bad signature");
  }
  if (event.type === "checkout.session.completed") {
    const session = event.data.object;
    await db.query("INSERT INTO credit_grants (user_id, credits) VALUES ($1, $2)", [session.client_reference_id, 100]);
    await db.query("UPDATE users SET credits = credits + 100 WHERE id = $1", [session.client_reference_id]);
  }
  res.sendStatus(200);
});

app.use(express.json());

app.get("/thumbnail", (req, res) => {
  exec(`convert uploads/${req.query.file} -resize 200x200 -`, { encoding: "buffer" }, (err, stdout) => {
    if (err) return res.status(500).json({ error: err.message, stack: err.stack });
    res.type("png").send(stdout);
  });
});

app.get("/me", (req, res) => {
  const claims = jwt.verify(String(req.headers.authorization).replace("Bearer ", ""), JWT_SECRET);
  res.json(claims);
});

app.listen(8080, () => console.log("listening", renderer.options.rejectUnauthorized));
