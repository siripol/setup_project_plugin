// Tier 2 — local agent loop via @anthropic-ai/claude-agent-sdk.
//
// Runs a Read/Glob/Grep agent against the current directory and delegates
// the heavy review pass to the code-reviewer subagent. Hooks wire in
// rate-limit, chokepoint-gate, and audit when present.
//
// Run with `npm run agent`.

import { query } from "@anthropic-ai/claude-agent-sdk";

async function loadHook(modulePath: string, exportName: string): Promise<any | undefined> {
  try {
    const mod = await import(modulePath);
    return mod?.[exportName];
  } catch {
    return undefined;
  }
}

const DEFAULT_PROMPT =
  "Summarize this project's structure: read AGENTS.md and the top-level files; report owners, key invariants, and any obvious risks.";

function hookBlock(audit: any, rate: any, choke: any): any {
  const pre: any[] = [];
  if (rate) pre.push({ matcher: ".*",         hooks: [rate] });
  if (choke) pre.push({ matcher: "Edit|Write", hooks: [choke] });
  if (audit) pre.push({ matcher: ".*",         hooks: [audit] });

  const hooks: any = {};
  if (pre.length) hooks.PreToolUse = pre;
  if (audit) {
    hooks.PostToolUse = [{ matcher: ".*", hooks: [audit] }];
    hooks.UserPromptSubmit = [{ matcher: ".*", hooks: [audit] }];
    hooks.Stop = [{ matcher: ".*", hooks: [audit] }];
  }
  return hooks;
}

export async function runAgent(prompt: string = DEFAULT_PROMPT): Promise<string[]> {
  if (!process.env.ANTHROPIC_API_KEY) {
    throw new Error("set ANTHROPIC_API_KEY in env");
  }

  const auditHook = await loadHook("../.claude/hooks/audit.js", "auditHook");
  const rateLimitHook = await loadHook("../.claude/hooks/rate-limit.js", "rateLimitHook");
  const chokeHook = await loadHook("../.claude/hooks/chokepoint-gate.js", "chokepointGateHook");

  const options = {
    allowedTools: ["Read", "Glob", "Grep", "Agent"] as const,
    agents: {
      "code-reviewer": {
        description: "Reviews code for bugs, style, and security.",
        prompt: "Analyze code quality and suggest improvements.",
        tools: ["Read", "Glob", "Grep"] as const,
      },
    },
    hooks: hookBlock(auditHook, rateLimitHook, chokeHook),
  };

  const captured: string[] = [];
  for await (const message of query({ prompt, options })) {
    if ("result" in message && typeof (message as any).result === "string") {
      captured.push((message as any).result);
      console.log((message as any).result);
    }
  }
  return captured;
}

async function main(): Promise<void> {
  const prompt = process.argv.slice(2).join(" ") || DEFAULT_PROMPT;
  await runAgent(prompt);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
