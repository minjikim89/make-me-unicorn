import { Hono } from "hono";
import { cors } from "hono/cors";
const app = new Hono<{ Bindings: { RL: any } }>();
app.use("*", cors());
app.use("*", async (c, next) => { const { success } = await c.env.RL.limit({ key: c.req.header("cf-connecting-ip") ?? "" }); return success ? next() : c.text("slow down", 429); });
app.get("/", (c) => c.text("ok"));
export default app;
