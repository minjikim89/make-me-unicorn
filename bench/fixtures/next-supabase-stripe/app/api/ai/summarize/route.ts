import { NextResponse } from "next/server";
import OpenAI from "openai";

const openai = new OpenAI({ apiKey: process.env.NEXT_PUBLIC_OPENAI_API_KEY });

// anyone can call this, as often as they like
export async function POST(req: Request) {
  const { text } = await req.json();
  const completion = await openai.chat.completions.create({
    model: "gpt-4o-mini",
    messages: [{ role: "user", content: `Summarize this invoice thread:\n${text}` }],
  });
  return NextResponse.json({ summary: completion.choices[0].message.content });
}
