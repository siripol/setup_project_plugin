"""Markdown renderer for /sn-session-report.

Pure function `render_markdown(payload, project, window, today)` takes the
upstream analyzer's JSON payload (already filtered to a single project) and
returns a Markdown report body. Stdlib only; no I/O.
"""
from __future__ import annotations

from typing import Any


def render_markdown(
    payload: dict,
    project: str,
    window: str,
    today: str,
    *,
    project_name: str | None = None,
) -> str:
    """Return the Markdown body for a session report.

    `payload` is the analyzer JSON. `project` is the encoded project key
    (e.g. `-Users-siripol-Claude-setup-project-plugin`) used to filter
    cache_breaks + top_prompts against the analyzer payload. `window` is the
    human label ("7d", "all"). `today` is YYYY-MM-DD for frontmatter dates
    (passed in so the function stays pure and testable).

    `project_name` (keyword-only) is the human-readable directory name used
    in the vault path + frontmatter — typically `Path.cwd().name`. Falls
    back to a best-effort recovery from the encoded key when not supplied,
    which is lossy (`_` and `/` both become `-` in the encoded form).
    """
    overall = payload.get("overall", {}) or {}
    by_project = payload.get("by_project", {}) or {}
    by_subagent = payload.get("by_subagent_type", {}) or {}
    cache_breaks_all = payload.get("cache_breaks", []) or []
    top_prompts_all = payload.get("top_prompts", []) or []

    proj_stats = by_project.get(project, {}) or {}
    proj_input = proj_stats.get("input_tokens", {}) or {}
    proj_sub = proj_stats.get("subagent", {}) or {}
    proj_hours = proj_stats.get("hours", {}) or {}

    cache_breaks = [c for c in cache_breaks_all if c.get("project") == project]
    top_prompts = [p for p in top_prompts_all if p.get("project") == project][:10]

    proj_total = (
        (proj_input.get("total", 0) or 0)
        + (proj_stats.get("output_tokens", 0) or 0)
    )

    display_name = project_name if project_name else _human_project(project)

    lines: list[str] = []
    lines.append("---")
    lines.append(f"topic: session-report-{today.replace('-', '')}")
    lines.append(f"bucket: projects/{display_name}")
    lines.append(f"origin_project: {display_name}")
    lines.append(f"first_seen: {today}")
    lines.append(f"last_updated: {today}")
    lines.append(f"window: {window}")
    lines.append(
        "tags: [knowledge, session-report, tokens, cache, "
        f"{display_name}]"
    )
    lines.append("---")
    lines.append("")

    lines.append(
        f"# Session report — {display_name} — {window} "
        f"ending {today}"
    )
    lines.append("")
    lines.append(
        f"Source analyzer: `{payload.get('root', '~/.claude/projects')}` "
        f"at `{payload.get('generated_at', '')}`."
    )
    lines.append("")

    # ----- Headline -----------------------------------------------------
    lines.append("## Headline")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Total tokens (input + output) | {_fmt(proj_total)} |")
    lines.append(
        f"| Cache-hit % | {_fmt_pct(proj_input.get('pct_cached'))} |"
    )
    lines.append(f"| Sessions | {proj_stats.get('sessions', 0)} |")
    lines.append(f"| API calls | {proj_stats.get('api_calls', 0)} |")
    lines.append(
        f"| Wall-clock hours | {proj_hours.get('wall_clock', 0)} |"
    )
    lines.append(f"| Active hours | {proj_hours.get('active', 0)} |")
    lines.append(f"| Subagent calls | {proj_sub.get('calls', 0)} |")
    lines.append("")

    # ----- Anomalies ----------------------------------------------------
    lines.append("## Anomalies")
    lines.append("")
    anomalies = _build_anomalies(
        proj_stats, by_subagent, cache_breaks, top_prompts, proj_total
    )
    if anomalies:
        lines.extend(anomalies)
    else:
        lines.append(
            "> [!info] No anomalies detected against current thresholds."
        )
    lines.append("")

    # ----- Token breakdown ---------------------------------------------
    lines.append("## Token breakdown")
    lines.append("")
    lines.append("| Bucket | Tokens |")
    lines.append("|---|---|")
    lines.append(f"| Input — uncached | {_fmt(proj_input.get('uncached', 0))} |")
    lines.append(
        f"| Input — cache-create | {_fmt(proj_input.get('cache_create', 0))} |"
    )
    lines.append(
        f"| Input — cache-read | {_fmt(proj_input.get('cache_read', 0))} |"
    )
    lines.append(f"| Output | {_fmt(proj_stats.get('output_tokens', 0))} |")
    lines.append("")

    # ----- Top prompts -------------------------------------------------
    lines.append("## Top prompts")
    lines.append("")
    if top_prompts:
        lines.append("| Tokens | % of project | API calls | Subagent calls | Prompt |")
        lines.append("|---|---|---|---|---|")
        for p in top_prompts:
            tok = p.get("total_tokens", 0) or 0
            pct = (tok / proj_total * 100) if proj_total else 0
            text = _truncate(p.get("text", ""), 80)
            lines.append(
                f"| {_fmt(tok)} | {pct:.1f}% | {p.get('api_calls', 0)} | "
                f"{p.get('subagent_calls', 0)} | {text} |"
            )
    else:
        lines.append("_No prompts in this project within the window._")
    lines.append("")

    # ----- Subagent activity ------------------------------------------
    lines.append("## Subagent activity (cross-project)")
    lines.append("")
    if by_subagent:
        lines.append("| Type | Calls | Total tokens | Avg / call |")
        lines.append("|---|---|---|---|")
        for name, stats in _sorted_by_subagent(by_subagent):
            sub = stats.get("subagent", {}) or {}
            lines.append(
                f"| {name} | {sub.get('calls', 0)} | "
                f"{_fmt(sub.get('total_tokens', 0))} | "
                f"{_fmt(sub.get('avg_tokens_per_call', 0))} |"
            )
    else:
        lines.append("_No subagent activity recorded in the window._")
    lines.append("")
    lines.append(
        "> [!info] Subagent stats are global (the upstream analyzer does not "
        "split them per project). Treat as a session-wide signal."
    )
    lines.append("")

    # ----- Skill invocations -------------------------------------------
    lines.append("## Skill invocations (cross-project)")
    lines.append("")
    skill_counts = (overall.get("skill_invocations") or {})
    if skill_counts:
        lines.append("| Skill | Count |")
        lines.append("|---|---|")
        for name, count in sorted(
            skill_counts.items(), key=lambda kv: -kv[1]
        ):
            lines.append(f"| `{name}` | {count} |")
    else:
        lines.append("_No skill invocations recorded._")
    lines.append("")
    lines.append(
        "> [!info] Skill stats are global. Per-project rollup is not "
        "available from the upstream analyzer."
    )
    lines.append("")

    # ----- Cache breaks -------------------------------------------------
    lines.append("## Cache breaks (this project)")
    lines.append("")
    if cache_breaks:
        lines.append("| Timestamp | Uncached | Total | Trigger |")
        lines.append("|---|---|---|---|")
        for cb in cache_breaks:
            ctx = cb.get("context") or []
            trigger_text = ""
            for item in ctx:
                if item.get("here"):
                    trigger_text = _truncate(item.get("text", ""), 60)
                    break
            if not trigger_text and ctx:
                trigger_text = _truncate(ctx[-1].get("text", ""), 60)
            lines.append(
                f"| {cb.get('ts', '')} | {_fmt(cb.get('uncached', 0))} | "
                f"{_fmt(cb.get('total', 0))} | {trigger_text} |"
            )
    else:
        lines.append("_No cache-break events for this project._")
    lines.append("")

    # ----- Optimizations ------------------------------------------------
    lines.append("## Optimizations")
    lines.append("")
    opts = _build_optimizations(
        proj_stats, top_prompts, cache_breaks, by_subagent, proj_total
    )
    if opts:
        lines.extend(opts)
    else:
        lines.append("> [!tip] Nothing actionable surfaced this window.")
    lines.append("")

    # ----- See also -----------------------------------------------------
    lines.append("## See also")
    lines.append("")
    lines.append("- [[implementation-log]]")
    lines.append("- [[project-requirements]]")
    lines.append("- [[../../../global/shared/session-report-skill]]")
    lines.append("")

    return "\n".join(lines)


# ----- helpers ----------------------------------------------------------


def _human_project(encoded: str) -> str:
    """Reverse the analyzer's `/` and `_` → `-` encoding for display.

    We can only undo `/`→`-` reliably (path components); we keep dashes for
    the rest. The last segment is what we want for the project frontmatter.
    """
    if not encoded:
        return "unknown-project"
    # The encoded form starts with a leading dash and uses dashes for path
    # separators. Pick the trailing path component as the project name.
    trimmed = encoded.lstrip("-")
    parts = trimmed.split("-")
    # Heuristic: drop leading `Users/<user>/Claude/` style prefix when present.
    while parts and parts[0] in ("Users", "home", "Claude"):
        parts.pop(0)
    if parts and len(parts[0]) <= 3 and parts[0][0].islower():
        # likely a username segment (e.g. `siripol`) — keep it; just take the tail
        pass
    # Take the last "interesting" run as project name
    return parts[-1] if not parts else "-".join(parts[-3:]) if len(parts) >= 3 else "-".join(parts)


def _fmt(n: Any) -> str:
    """Human-friendly number: 1.2M / 850k / 42."""
    try:
        n = int(n)
    except (TypeError, ValueError):
        return "0"
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def _fmt_pct(p: Any) -> str:
    try:
        return f"{float(p):.1f}%"
    except (TypeError, ValueError):
        return "—"


def _truncate(text: str, n: int) -> str:
    text = (text or "").replace("|", "\\|").replace("\n", " ")
    return text if len(text) <= n else text[: n - 1] + "…"


def _sorted_by_subagent(by_sub: dict) -> list[tuple[str, dict]]:
    return sorted(
        by_sub.items(),
        key=lambda kv: -(kv[1].get("subagent", {}) or {}).get("total_tokens", 0),
    )


def _build_anomalies(
    proj_stats: dict,
    by_sub: dict,
    cache_breaks: list,
    top_prompts: list,
    proj_total: int,
) -> list[str]:
    out: list[str] = []
    pct = (proj_stats.get("input_tokens", {}) or {}).get("pct_cached")
    if pct is not None and pct < 85:
        out.append(
            f"> [!warning] Cache-hit {pct:.1f}% (below 85% target) — "
            "investigate cache-invalidation triggers."
        )

    for p in top_prompts:
        tok = p.get("total_tokens", 0) or 0
        if proj_total and (tok / proj_total) > 0.02:
            share = tok / proj_total * 100
            out.append(
                f"> [!warning] One prompt burned {share:.1f}% of project total — "
                f"`{_truncate(p.get('text', ''), 60)}` ({_fmt(tok)} tokens)."
            )
            break

    for name, stats in (by_sub or {}).items():
        sub = stats.get("subagent", {}) or {}
        avg = sub.get("avg_tokens_per_call", 0) or 0
        if avg > 1_000_000:
            out.append(
                f"> [!warning] Subagent `{name}` averaged {_fmt(avg)} tokens / "
                f"call — consider scope trimming or smaller model."
            )

    if len(cache_breaks) >= 3:
        out.append(
            f"> [!warning] {len(cache_breaks)} cache-break events for this "
            "project this window — likely a recurring trigger."
        )

    if proj_stats.get("sessions", 0) and proj_total < 100_000:
        out.append(
            f"> [!success] Light week: {_fmt(proj_total)} tokens across "
            f"{proj_stats.get('sessions', 0)} session(s)."
        )

    return out[:5]


def _build_optimizations(
    proj_stats: dict,
    top_prompts: list,
    cache_breaks: list,
    by_sub: dict,
    proj_total: int,
) -> list[str]:
    out: list[str] = []

    for p in top_prompts[:1]:
        tok = p.get("total_tokens", 0) or 0
        if proj_total and (tok / proj_total) > 0.02:
            out.append(
                f"> [!tip] Scope or cache the top prompt "
                f"(`{_truncate(p.get('text', ''), 50)}`) — saves "
                f"~{_fmt(int(tok * 0.5))} if cached."
            )

    for name, stats in (by_sub or {}).items():
        sub = stats.get("subagent", {}) or {}
        if (sub.get("avg_tokens_per_call", 0) or 0) > 1_000_000:
            out.append(
                f"> [!tip] Reduce per-call context for subagent `{name}` "
                "(currently >1M tokens / call)."
            )
            break

    if cache_breaks and len(cache_breaks) >= 2:
        out.append(
            "> [!tip] Investigate the most common trigger across "
            f"{len(cache_breaks)} cache-break events — usually a slash "
            "command or `/clear` mid-session."
        )

    pct = (proj_stats.get("input_tokens", {}) or {}).get("pct_cached")
    if pct is not None and pct < 85:
        out.append(
            "> [!tip] Cache-hit under 85% suggests system-prompt churn — "
            "review hooks / context blocks that change between turns."
        )

    return out[:4]
