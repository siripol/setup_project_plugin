// Tier 3 — Managed Agents session driver via @anthropic-ai/sdk.
// Runnable stub. Set AGENT_ID env then `npm run client`.

import Anthropic from "@anthropic-ai/sdk";

export async function runSession(agentId?: string): Promise<void> {
  if (!process.env.ANTHROPIC_API_KEY) {
    throw new Error("set ANTHROPIC_API_KEY in env");
  }
  const id = agentId ?? process.env.AGENT_ID;
  if (!id) {
    throw new Error("set AGENT_ID or pass it to runSession()");
  }

  // Pseudocode (uncomment after `npm install`):
  //
  //   const client = new Anthropic();
  //   const session = await client.beta.sessions.create({ agent_id: id });
  //   for await (const event of client.beta.sessions.events.stream(session.id)) {
  //     console.log(event);
  //   }
  void Anthropic; // referenced for future use
  console.log(`client.ts stub — would create Managed Agent session for agent ${id}`);
}

if (import.meta.url === `file://${process.argv[1]}`) {
  runSession().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}
