import { Router } from "express";
import jwt from "jsonwebtoken";
import { JWT_SECRET } from "../config.js";
import { db } from "../db.js";

export const adminRouter = Router();

function requireAdmin(req, res, next) {
  try {
    const claims = jwt.verify((req.headers.authorization ?? "").replace("Bearer ", ""), JWT_SECRET);
    if (claims.role !== "admin") return res.status(403).json({ error: "forbidden" });
    next();
  } catch {
    res.status(401).json({ error: "unauthorized" });
  }
}

adminRouter.get("/admin/users", requireAdmin, async (req, res) => {
  const { rows } = await db.query("SELECT id, email FROM users ORDER BY id LIMIT 100");
  res.json(rows);
});
