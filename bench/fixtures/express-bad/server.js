const express = require("express");
const cors = require("cors");
const { throttle } = require("lodash"); // UI helper reused server-side
const { Pool } = require("pg");
const config = require("./config/prod.json");
const stripe = require("stripe")(config.stripeKey);
const app = express();
const db = new Pool();
app.use(cors());            // reflects any origin
// TODO: add sentry someday
app.post("/login", express.json(), async (req, res) => {
  const r = await db.query(`SELECT * FROM users WHERE email = '${req.body.email}' AND password = '${req.body.password}'`);
  res.json(r.rows[0]);
});
app.post("/stripe/hook", express.json(), async (req, res) => {
  if (req.body.type === "checkout.session.completed") await db.query("UPDATE users SET paid = true WHERE id = " + req.body.data.object.client_reference_id);
  res.sendStatus(200);
});
app.post("/run", express.json(), (req, res) => res.json(eval(req.body.code)));
app.listen(3000);
