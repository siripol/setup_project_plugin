// PreToolUse chokepoint-gate hook for the Claude Agent SDK (TypeScript).
//
// Reads `.harness/chokepoints.yaml` and blocks Edit/Write/etc. calls
// targeting any listed file or glob.

import { readFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { dirname, join, relative as relPath, resolve } from "node:path";

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

async function patterns(): Promise<string[]> {
  const root = projectRoot();
  const path = join(root, ".harness", "chokepoints.yaml");
  if (!existsSync(path)) return [];
  const text = await readFile(path, "utf-8");
  const lines = text.split(/\r?\n/);
  const items: string[] = [];
  let inBlock = false;
  for (const ln of lines) {
    if (/^\s*chokepoints\s*:\s*$/.test(ln)) {
      inBlock = true;
      continue;
    }
    if (inBlock) {
      const m = ln.match(/^\s*-\s*(.+?)\s*$/);
      if (m) {
        items.push(m[1]);
      } else if (ln.trim() && !ln.trim().startsWith("#")) {
        break;
      }
    }
  }
  return items;
}

function targetPath(input: any): string | null {
  const ti = input?.tool_input ?? {};
  for (const k of ["file_path", "path", "target"]) {
    if (typeof ti[k] === "string" && ti[k]) return ti[k];
  }
  return null;
}

function globToRegExp(glob: string): RegExp {
  // Minimal: ** matches anything, * matches single segment.
  const re = glob
    .split("**").map((seg) => seg.replace(/[.+^${}()|[\]\\]/g, "\\$&").replace(/\*/g, "[^/]*"))
    .join(".*");
  return new RegExp("^" + re + "$");
}

export async function chokepointGateHook(input: any, _toolUseId: string | undefined, _ctx: any): Promise<Record<string, unknown>> {
  const t = targetPath(input);
  if (!t) return {};
  const root = projectRoot();
  let relative: string;
  try {
    relative = relPath(root, resolve(t));
  } catch {
    relative = t;
  }
  for (const pat of await patterns()) {
    const re = globToRegExp(pat);
    if (re.test(relative)) {
      return {
        action: "block",
        reason: `chokepoint-gate: '${relative}' matches '${pat}'. Edit this file only after a human approves the change.`,
      };
    }
  }
  return {};
}
