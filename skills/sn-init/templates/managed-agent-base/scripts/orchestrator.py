"""Spec-loop orchestrator skeleton.

State machine that drives one REQ through the spec-loop phases. Subagent
invocations are stubbed — `invoke_subagent()` is the only function the
lang-specific runner needs to override to wire the real Claude SDK.

CLI:
    python3 scripts/orchestrator.py plan SPRINT-NNN          # impact + planner
    python3 scripts/orchestrator.py run SPRINT-NNN           # full cycle
    python3 scripts/orchestrator.py phase REQ-NNN <phase>    # run one phase
    python3 scripts/orchestrator.py status                   # print state

Phases (in order):
    impact → plan → decompose → execute → test → integrate → adversary →
    evaluate → curate → done

State persisted to .sn-init/workflow-state.json (shared with safety.py).
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Allow `python3 scripts/orchestrator.py ...`
sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    import safety  # type: ignore
except Exception:  # pragma: no cover
    safety = None  # type: ignore


PHASES = (
    "impact",
    "plan",
    "decompose",
    "execute",
    "test",
    "integrate",
    "adversary",
    "evaluate",
    "curate",
    "done",
)


PHASE_TO_SUBAGENT = {
    "impact":    "impact-analyzer",
    "plan":      "planner",
    "decompose": "task-decomposer",
    "execute":   "task-executor",
    "test":      "task-tester",
    "integrate": "integration-tester",
    "adversary": "adversary",
    "evaluate":  "evaluator",
    "curate":    "knowledge-curator",
}


@dataclass
class Orchestrator:
    sprint_id: str
    project_root: Path

    # --- state ---

    def _state(self) -> dict:
        if safety is None:
            path = self.project_root / ".sn-init" / "workflow-state.json"
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return safety.load()

    def _save(self, state: dict) -> None:
        if safety is None:
            path = self.project_root / ".sn-init" / "workflow-state.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
            return
        safety.save(state)

    # --- run ---

    def list_reqs(self) -> list[str]:
        sprint_dir = next(
            (self.project_root / "docs" / "sprints" / "active").glob(f"{self.sprint_id}-*"),
            None,
        )
        if sprint_dir is None:
            return []
        return sorted(p.stem for p in (sprint_dir / "requirements").glob("REQ-*.md"))

    def run(self) -> int:
        reqs = self.list_reqs()
        if not reqs:
            print(f"orchestrator: no REQs found in {self.sprint_id}", file=sys.stderr)
            return 2

        state = self._state()
        state.setdefault("sprints", {})[self.sprint_id] = {
            "status": "running",
            "reqs": reqs,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        state["active_sprint"] = self.sprint_id
        self._save(state)

        for req_id in reqs:
            if safety and safety.is_in_cooldown(req_id):
                print(f"orchestrator: {req_id} in cooldown — skipping", file=sys.stderr)
                continue
            self._run_one_req(req_id)

        state = self._state()
        state["sprints"][self.sprint_id]["status"] = "completed"
        self._save(state)
        return 0

    def _run_one_req(self, req_id: str) -> None:
        for phase in PHASES:
            if phase == "done":
                continue
            verdict = self.phase(req_id, phase)
            if verdict.get("status") != "ok":
                print(
                    f"orchestrator: {req_id} {phase} → {verdict}",
                    file=sys.stderr,
                )
                return

    # --- phases ---

    def phase(self, req_id: str, phase: str) -> dict:
        if phase not in PHASE_TO_SUBAGENT and phase != "done":
            return {"status": "error", "reason": f"unknown phase: {phase}"}
        subagent = PHASE_TO_SUBAGENT.get(phase, "")
        prompt = self._prompt_for_phase(req_id, phase)
        result = invoke_subagent(subagent, prompt, context={"req_id": req_id, "phase": phase})
        self._record_phase(req_id, phase, result)
        if phase == "evaluate" and safety is not None:
            safety.record_progress(req_id, result.get("eval_score"))
        return result

    def _prompt_for_phase(self, req_id: str, phase: str) -> str:
        return (
            f"You are the {PHASE_TO_SUBAGENT.get(phase, phase)} subagent. "
            f"REQ id: {req_id}. Sprint: {self.sprint_id}. "
            f"Follow the subagent's capability manifest in "
            f".claude/agents/{PHASE_TO_SUBAGENT.get(phase, phase)}.md."
        )

    def _record_phase(self, req_id: str, phase: str, result: dict) -> None:
        state = self._state()
        active = state.setdefault("active_phase", {})
        active[req_id] = phase
        state.setdefault("phase_history", {}).setdefault(req_id, []).append({
            "phase": phase,
            "result": result,
            "ts": datetime.now(timezone.utc).isoformat(),
        })
        self._save(state)


# ---------------------------------------------------------------------------
# Subagent invocation (override in lang-specific runner)


def invoke_subagent(subagent: str, prompt: str, context: dict) -> dict:
    """Stub. Lang-specific orchestrators (src/orchestrator.{py,ts,go}) replace
    this with a real SDK call.

    Returns a verdict dict. Required keys:
      status: "ok" | "blocked" | "failed"
      reason: str (when blocked/failed)
    Optional:
      eval_score: int (0-100) — only emitted by evaluator phase
    """
    return {
        "status": "ok",
        "subagent": subagent,
        "prompt": prompt[:160],
        "context": context,
        "note": "stub — wire to Claude Agent SDK in src/orchestrator.{py,ts,go}",
    }


# ---------------------------------------------------------------------------
# CLI


def _cli(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(
            "usage: orchestrator.py "
            "{run SPRINT-NNN | plan SPRINT-NNN | phase REQ-NNN PHASE | status}"
        )
        return 0

    cmd = argv[0]
    root = Path.cwd()

    if cmd == "status":
        if safety is None:
            return 2
        state = safety.load()
        keys = ("active_sprint", "sprints", "active_phase", "phase_history")
        print(json.dumps({k: state.get(k) for k in keys}, indent=2, default=str))
        return 0

    if cmd == "run":
        if len(argv) < 2:
            print("usage: orchestrator.py run SPRINT-NNN", file=sys.stderr)
            return 2
        return Orchestrator(sprint_id=argv[1], project_root=root).run()

    if cmd == "plan":
        if len(argv) < 2:
            print("usage: orchestrator.py plan SPRINT-NNN", file=sys.stderr)
            return 2
        orch = Orchestrator(sprint_id=argv[1], project_root=root)
        for req in orch.list_reqs():
            orch.phase(req, "impact")
            orch.phase(req, "plan")
        return 0

    if cmd == "phase":
        if len(argv) < 3:
            print("usage: orchestrator.py phase REQ-NNN PHASE", file=sys.stderr)
            return 2
        # Try to derive sprint from REQ presence; fall back to "SPRINT-001".
        orch = Orchestrator(sprint_id="SPRINT-active", project_root=root)
        result = orch.phase(argv[1], argv[2])
        print(json.dumps(result, indent=2))
        return 0

    print(f"unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))
