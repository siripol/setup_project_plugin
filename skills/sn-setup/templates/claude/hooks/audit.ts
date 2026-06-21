// Audit hook for the Claude Agent SDK (TypeScript).
//
// Wire via:
//
//   import { query, type HookCallback } from "@anthropic-ai/claude-agent-sdk";
//   import { auditHook } from "../.claude/hooks/audit.js";
//
//   const options = {
//     hooks: {
//       PreToolUse:        [{ matcher: ".*", hooks: [auditHook] }],
//       PostToolUse:       [{ matcher: ".*", hooks: [auditHook] }],
//       UserPromptSubmit:  [{ matcher: ".*", hooks: [auditHook] }],
//       Stop:              [{ matcher: ".*", hooks: [auditHook] }],
//     },
//   };

import { appendFile, mkdir, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { createHash } from "node:crypto";

const MAX_INLINE_BYTES = 2048;

function projectRoot(start: string = process.cwd()): string {
  let p = resolve(start);
  while (p !== dirname(p)) {
    if (existsSync(join(p, ".sn-init")) || existsSync(join(p, "CLAUDE.md"))) {
      return p;
    }
    p = dirname(p);
  }
  return resolve(start);
}

function logPaths(sessionId: string): { logPath: string; blobDir: string } {
  const root = projectRoot();
  const date = new Date().toISOString().slice(0, 10);
  const logDir = join(root, ".sn-init", "logs");
  const blobDir = join(logDir, "blobs");
  return { logPath: join(logDir, `exec-${date}-${sessionId}.jsonl`), blobDir };
}

async function truncate(value: unknown): Promise<{ inline: unknown; truncated: boolean; blob?: string }> {
  const serialized = typeof value === "string" ? value : JSON.stringify(value);
  const raw = Buffer.from(serialized ?? "", "utf-8");
  if (raw.byteLength <= MAX_INLINE_BYTES) {
    return { inline: value, truncated: false };
  }
  const blob = createHash("sha256").update(raw).digest("hex").slice(0, 16);
  const { blobDir } = logPaths("blob-spill");
  await mkdir(blobDir, { recursive: true });
  await writeFile(join(blobDir, `${blob}.txt`), raw);
  return { inline: serialized.slice(0, MAX_INLINE_BYTES), truncated: true, blob };
}

export async function auditHook(input: any, _toolUseId: string | undefined, context: any): Promise<Record<string, unknown>> {
  const sessionId: string =
    context?.session_id ?? process.env.CLAUDE_SESSION_ID ?? "unknown";
  const { logPath } = logPaths(sessionId);

  try {
    await mkdir(dirname(logPath), { recursive: true });
  } catch {
    return {};
  }

  const event = input?.hook_event_name ?? input?.event ?? "tool";
  const toolName = input?.tool_name ?? input?.tool?.name;
  const toolInput = input?.tool_input;
  const toolOutput = input?.tool_output ?? input?.output;

  const record: Record<string, unknown> = {
    ts: new Date().toISOString(),
    session_id: sessionId,
    event,
    tool_name: toolName,
    model: input?.model,
    usage: input?.usage,
    obsidian_backend: null,
  };
  if (_toolUseId) record.tool_use_id = _toolUseId;
  if (toolInput !== undefined) record.tool_input = toolInput;
  if (toolOutput !== undefined) {
    const t = await truncate(toolOutput);
    record.tool_output = t.inline;
    if (t.truncated) {
      record.truncated = true;
      record.blob = t.blob;
    }
  }

  try {
    await appendFile(logPath, JSON.stringify(record) + "\n", "utf-8");
  } catch {
    // never block the session
  }
  return {};
}
