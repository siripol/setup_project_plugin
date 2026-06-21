// Tier-2 spec-loop orchestrator wrapper.
//
// Run via `npm run orchestrator -- SPRINT-NNN`. Delegates state management
// to `scripts/orchestrator.py` (invoked through child_process) so the wire
// shape stays consistent across langs.

import { spawn } from "node:child_process";

async function invokeSubagent(subagent: string, prompt: string): Promise<Record<string, unknown>> {
  try {
    const { query } = await import("@anthropic-ai/claude-agent-sdk");
    const out: string[] = [];
    for await (const message of query({
      prompt,
      options: {
        allowedTools: ["Read", "Glob", "Grep", "Edit", "Write", "Bash", "Agent"],
        agents: {
          [subagent]: {
            description: `Spec-loop ${subagent} phase`,
            prompt: `You are the ${subagent} subagent. Follow .claude/agents/${subagent}.md.`,
            tools: ["Read", "Glob", "Grep"],
          },
        },
      },
    })) {
      if ((message as any)?.result !== undefined) out.push((message as any).result);
    }
    const verdict: Record<string, unknown> = { status: "ok", subagent };
    if (subagent === "evaluator" && out.length) {
      try {
        Object.assign(verdict, JSON.parse(out[out.length - 1]));
      } catch {
        verdict.raw = out[out.length - 1];
      }
    }
    return verdict;
  } catch (err) {
    return { status: "ok", note: "@anthropic-ai/claude-agent-sdk not installed; stub call" };
  }
}

async function main(): Promise<number> {
  const sprintId = process.argv[2];
  if (!sprintId) {
    console.error("usage: src/orchestrator.ts SPRINT-NNN");
    return 2;
  }
  if (!process.env.ANTHROPIC_API_KEY) {
    console.error("warning: ANTHROPIC_API_KEY not set; subagent calls will stub");
  }

  // Delegate the state machine to the Python orchestrator. The TS side only
  // handles SDK invocation; phase dispatch + state persistence stays in one
  // language to avoid duplicating logic.
  return new Promise<number>((resolve) => {
    const proc = spawn("python3", ["scripts/orchestrator.py", "run", sprintId], { stdio: "inherit" });
    proc.on("exit", (code) => resolve(code ?? 1));
    proc.on("error", (err) => {
      console.error(err);
      resolve(1);
    });
  });
}

// `invokeSubagent` is exported so unit tests can stub or call it directly.
export { invokeSubagent };

main().then((rc) => process.exit(rc));
