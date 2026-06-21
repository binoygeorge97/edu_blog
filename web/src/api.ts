// Types mirror app/models.py exactly (snake_case as serialized by FastAPI).

export type ChatRole = "user" | "assistant";
export interface ChatTurn {
  role: ChatRole;
  content: string;
}

export type Verdict = "supports" | "refutes" | "unclear";
export interface AgentComment {
  agent: "generator" | "critic" | "verifier";
  role: string;
  content: string;
  claim: string | null;
  verdict: Verdict | null;
  url: string | null;
  claim_id: string | null;
}

export type ParagraphStatus = "verified" | "disputed" | "hallucination" | "neutral";
export interface Paragraph {
  id: string;
  status: ParagraphStatus;
  text: string;
}

export interface BlogPost {
  title: string;
  paragraphs: Paragraph[];
}

export type ConfidenceLevel = "high" | "medium" | "low";
export interface BlogPostResult {
  answer: BlogPost;
  comments: AgentComment[];
  confidence: number;
  confidence_level: ConfidenceLevel;
}

const API = "/api"; // proxied to the FastAPI backend by Vite (see vite.config.ts)

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`${path} failed (${res.status}): ${detail.slice(0, 300)}`);
  }
  return res.json() as Promise<T>;
}

/** Tutoring phase — plain conversation, no fact-checking. */
export async function chat(messages: ChatTurn[]): Promise<string> {
  const { reply } = await post<{ reply: string }>("/chat", { messages });
  return reply;
}

/** Conversion phase — turn the conversation into a reviewed blog post. */
export async function convert(messages: ChatTurn[]): Promise<BlogPostResult> {
  return post<BlogPostResult>("/convert", { messages });
}

/** Reply to an agent's comment — continues the tutoring conversation. */
export async function replyToComment(
  comment: AgentComment,
  followup: string,
  messages: ChatTurn[]
): Promise<string> {
  const { reply } = await post<{ reply: string }>("/reply", {
    comment,
    followup,
    messages,
  });
  return reply;
}
