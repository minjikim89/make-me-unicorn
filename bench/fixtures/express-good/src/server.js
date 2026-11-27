import * as Sentry from "@sentry/node";
import cors from "cors";
import express from "express";
import rateLimit from "express-rate-limit";
import { ALLOWED_ORIGINS } from "./config.js";
import { adminRouter } from "./routes/admin.js";
import { authRouter } from "./routes/auth.js";
import { billingRouter } from "./routes/billing.js";

Sentry.init({ dsn: process.env.SENTRY_DSN });

const app = express();
app.use(cors({ origin: ALLOWED_ORIGINS, credentials: true }));
app.use("/billing/webhook", express.raw({ type: "application/json" }));
app.use(express.json());
app.use("/auth", rateLimit({ windowMs: 60_000, limit: 10 }), authRouter);
app.use("/billing", billingRouter);
app.use("/admin", adminRouter);

app.use((err, req, res, next) => {
  Sentry.captureException(err);
  res.status(500).json({
    error: "internal error",
    ...(process.env.NODE_ENV === "development" && { stack: err.stack }),
  });
});

app.listen(3000);
