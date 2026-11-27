import bcrypt from "bcryptjs";
import crypto from "node:crypto";
import { Router } from "express";
import jwt from "jsonwebtoken";
import { JWT_SECRET } from "../config.js";
import { db } from "../db.js";
import { sendMail } from "../mail.js";

export const authRouter = Router();
const SLUG = /^[a-z0-9-]+$/;

authRouter.post("/login", async (req, res) => {
  const { rows } = await db.query("SELECT id, password_hash FROM users WHERE email = $1", [req.body.email]);
  const user = rows[0];
  if (!user || !(await bcrypt.compare(req.body.password, user.password_hash))) {
    return res.status(401).json({ error: "bad credentials" });
  }
  res.json({ token: jwt.sign({ sub: user.id }, JWT_SECRET, { expiresIn: "1h" }) });
});

authRouter.post("/forgot-password", async (req, res) => {
  const token = crypto.randomBytes(32).toString("hex");
  const hash = crypto.createHash("sha256").update(token).digest("hex");
  await db.query("UPDATE users SET reset_token_hash = $1, reset_expires = now() + interval '15 minutes' WHERE email = $2", [hash, req.body.email]);
  await sendMail(req.body.email, "reset-password", { token });
  res.json({ ok: true });
});

authRouter.get("/workspaces/:slug", async (req, res) => {
  // RegExp.exec on request data is not code execution
  if (!SLUG.exec(req.params.slug)) return res.status(400).json({ error: "bad slug" });
  const column = req.query.sort === "name" ? "name" : "created_at";
  const { rows } = await db.query(`SELECT id, name FROM workspaces WHERE slug = $1 ORDER BY ${column}`, [req.params.slug]);
  res.json(rows);
});
