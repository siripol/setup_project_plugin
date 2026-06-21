// Tier 3 — Managed Agents session driver via @anthropic-ai/sdk.
//
// Creates a session against a previously-applied Managed Agent and streams
// events. Set AGENT_ID and ANTHROPIC_API_KEY, then `npm run client`.

import Anthropic from "@anthropic-ai/sdk";

export async function runSession(agentId?: string, message: string = "Hello from sn-init."): Promise<number> {
  if (!process.env.ANTHROPIC_API_KEY) {
    throw new Error("set ANTHROPIC_API_KEY in env");
  }
  const id = agentId ?? process.env.AGENT_ID;
  if (!id) {
    throw new Error("set AGENT_ID or pass it to runSession()");
  }

  const client = new Anthropic();
  const session = await (client as any).beta.sessions.create({ agent_id: id });
  console.log(`session: ${session.id}`);

  await (client as any).beta.sessions.messages.create({
    session_id: session.id,
    content: message,
  });

  for await (const event of (client as any).beta.sessions.events.stream(session.id)) {
    console.log(event);
    if (event?.type === "session.idle") break;
  }
  return 0;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  runSession().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}
