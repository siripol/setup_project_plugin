// PreToolUse rate-limit hook for the Claude Agent SDK (TypeScript).
//
// Caps (env):
//   SN_MAX_CALLS_PER_HOUR  = 200
//   SN_MAX_TOKENS_PER_HOUR = 2_000_000

import { readFile, writeFile, mkdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";

const MAX_CALLS = Number(process.env.SN_MAX_CALLS_PER_HOUR ?? "200");
const MAX_TOKENS = Number(process.env.SN_MAX_TOKENS_PER_HOUR ?? "2000000");

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

function statePath(): string {
  return join(projectRoot(), ".sn-init", "workflow-state.json");
}

async function loadState(): Promise<any> {
  try {
    return JSON.parse(await readFile(statePath(), "utf-8"));
  } catch {
    return {};
  }
}

async function saveState(state: any): Promise<void> {
  const sp = statePath();
  await mkdir(dirname(sp), { recursive: true });
  await writeFile(sp, JSON.stringify(state, null, 2) + "\n", "utf-8");
}

export async function rateLimitHook(input: any, _toolUseId: string | undefined, _ctx: any): Promise<Record<string, unknown>> {
  const now = new Date();
  const state = await loadState();
  const window = state.rate_window ?? {};
  let started = window.window_start ? new Date(window.window_start) : null;
  let calls = Number(window.calls_this_hour ?? 0);
  let tokens = Number(window.tokens_this_hour ?? 0);

  if (started && now.getTime() - started.getTime() > 3600_000) {
    started = null;
    calls = 0;
    tokens = 0;
  }

  if (calls >= MAX_CALLS || tokens >= MAX_TOKENS) {
    return {
      action: "block",
      reason: `sn-init rate limit: ${calls}/${MAX_CALLS} calls, ${tokens}/${MAX_TOKENS} tokens this hour. Wait or raise SN_MAX_*_PER_HOUR.`,
    };
  }

  // Record the call.
  if (!started) {
    state.rate_window = { window_start: now.toISOString(), calls_this_hour: 0, tokens_this_hour: 0 };
  }
  state.rate_window = state.rate_window ?? {};
  state.rate_window.calls_this_hour = (Number(state.rate_window.calls_this_hour ?? 0) || 0) + 1;
  const usage = input?.usage ?? {};
  state.rate_window.tokens_this_hour =
    (Number(state.rate_window.tokens_this_hour ?? 0) || 0) +
    Number(usage.input_tokens ?? 0) +
    Number(usage.output_tokens ?? 0);
  await saveState(state);
  return {};
}
