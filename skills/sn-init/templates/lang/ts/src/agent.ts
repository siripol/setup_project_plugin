// Tier 2 — local agent loop via @anthropic-ai/claude-agent-sdk.
// Runnable stub. Start with `npm run agent`.

import { query } from "@anthropic-ai/claude-agent-sdk";

// Optional audit hook (present when scaffolded without --no-audit-log).
let auditHook: any = undefined;
try {
  ({ auditHook } = await import("../.claude/hooks/audit.js"));
} catch {
  // audit hook not present; continue without it
}

async function main(): Promise<void> {
  if (!process.env.ANTHROPIC_API_KEY) {
    console.error("set ANTHROPIC_API_KEY in env");
    process.exit(1);
  }

  const hooks = auditHook
    ? {
        PreToolUse:       [{ matcher: ".*", hooks: [auditHook] }],
        PostToolUse:      [{ matcher: ".*", hooks: [auditHook] }],
        UserPromptSubmit: [{ matcher: ".*", hooks: [auditHook] }],
        Stop:             [{ matcher: ".*", hooks: [auditHook] }],
      }
    : undefined;

  const options = {
    allowedTools: ["Read", "Glob", "Grep", "Agent"] as const,
    agents: {
      "code-reviewer": {
        description: "Reviews code for bugs, style, and security.",
        prompt: "Analyze code quality and suggest improvements.",
        tools: ["Read", "Glob", "Grep"] as const,
      },
    },
    hooks,
  };

  const prompt = "List the files in this directory and summarize the project layout.";
  for await (const message of query({ prompt, options })) {
    if ("result" in message) {
      console.log(message.result);
    }
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
