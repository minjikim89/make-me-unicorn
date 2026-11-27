import { NextResponse } from "next/server";
import OpenAI from "openai";
import { z } from "zod";
import { aiLimiter } from "@/lib/ratelimit";
import { createClient } from "@/lib/supabase/server";

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
const Body = z.object({ text: z.string().max(8000) });

export async function POST(req: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  const { success } = await aiLimiter.limit(user.id);
  if (!success) return NextResponse.json({ error: "too many requests" }, { status: 429 });

  const parsed = Body.safeParse(await req.json());
  if (!parsed.success) return NextResponse.json({ error: "bad request" }, { status: 400 });

  const completion = await openai.chat.completions.create({
    model: "gpt-4o-mini",
    max_tokens: 300,
    messages: [{ role: "user", content: `Summarize:\n${parsed.data.text}` }],
  });
  return NextResponse.json({ summary: completion.choices[0].message.content });
}
