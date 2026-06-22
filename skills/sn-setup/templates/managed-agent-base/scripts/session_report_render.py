"""Markdown renderer for /sn-session-report.

Pure function `render_markdown(payload, project, window, today)` takes the
upstream analyzer's JSON payload (already filtered to a single project) and
returns a Markdown report body. Stdlib only; no I/O.
"""
from __future__ import annotations

import re
from typing import Any


# Anomaly thresholds — tunable via env vars at render time.
DEFAULT_CACHE_HIT_TARGET = 85.0
DEFAULT_PROMPT_SHARE_PCT = 2.0
DEFAULT_SUBAGENT_TOKENS_PER_CALL = 1_000_000
DEFAULT_CACHE_BREAK_CLUSTER = 3

# Tunability heuristics
REPEAT_MIN_COUNT = 3
LOW_OUTPUT_RATIO = 0.001
PROMPT_CACHE_TARGET = 60.0  # below = flag as cache-miss


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

    # ----- Augment prompts with tunability signals --------------------
    all_project_prompts = [p for p in top_prompts_all if p.get("project") == project]
    repeat_groups = _compute_repeat_groups(all_project_prompts)
    median_api_calls = _median([p.get("api_calls", 0) or 0 for p in all_project_prompts])

    augmented = [
        _augment_prompt(p, cache_breaks, repeat_groups, median_api_calls, proj_total)
        for p in all_project_prompts
    ]
    # Deduplicate by normalized text — collapse repeats into a single row
    # showing the SUM of tokens and the repeat count, so the table reads as
    # one row per logical user intent.
    augmented = _dedup_by_normalized_text(augmented)
    # Sort by tunability score (desc); fall back to total_tokens.
    augmented.sort(
        key=lambda p: (-p["tunability_score"], -(p.get("total_tokens") or 0)),
    )
    top_tunable = augmented[:10]

    # ----- Top prompts (sorted by tunability) -------------------------
    lines.append("## Top prompts (by tunability)")
    lines.append("")
    lines.append(
        "Sorted by `tunability_score` — composite of repeat count, "
        "cache-miss share, subagent fan-out, API-call thrash, and "
        "output-ratio waste. Higher score = more likely to pay off if "
        "tuned. `reason` labels the dominant signal."
    )
    lines.append("")
    if top_tunable:
        lines.append(
            "| Score | Reason | Tokens | % proj | Cache-hit | Cache breaks "
            "| API calls | Subagent | Repeats | Prompt |"
        )
        lines.append("|---|---|---|---|---|---|---|---|---|---|")
        for p in top_tunable:
            tok = p.get("total_tokens", 0) or 0
            pct = (tok / proj_total * 100) if proj_total else 0
            text = _truncate(p.get("text", ""), 60)
            lines.append(
                f"| {p['tunability_score']:.0f} "
                f"| `{p['reason']}` "
                f"| {_fmt(tok)} "
                f"| {pct:.1f}% "
                f"| {p['cache_hit_pct']:.0f}% "
                f"| {p['cache_break_count']} "
                f"| {p.get('api_calls', 0)} "
                f"| {p.get('subagent_calls', 0)} "
                f"| {p['repeat_count']} "
                f"| {text} |"
            )
    else:
        lines.append("_No prompts in this project within the window._")
    lines.append("")

    # ----- Repeats ----------------------------------------------------
    lines.append("## Repeated prompts (skill candidates)")
    lines.append("")
    repeated = [
        {"text": text, "count": count, "tokens": sum(
            p.get("total_tokens", 0) or 0
            for p in all_project_prompts
            if _normalize_prompt_text(p.get("text", "")) == text
        )}
        for text, count in repeat_groups.items()
        if count >= REPEAT_MIN_COUNT
    ]
    repeated.sort(key=lambda r: -r["tokens"])
    if repeated:
        lines.append(
            "Prompts typed ≥ "
            f"{REPEAT_MIN_COUNT} times. Highest-ROI tuning targets — "
            "promote to a `/sn-<slug>` skill or CLAUDE.md macro and you "
            "stop paying that token cost on every replay."
        )
        lines.append("")
        lines.append("| Count | Total tokens | Normalized prompt |")
        lines.append("|---|---|---|")
        for r in repeated[:10]:
            lines.append(
                f"| {r['count']}× | {_fmt(r['tokens'])} | "
                f"{_truncate(r['text'], 80)} |"
            )
    else:
        lines.append(
            f"_No prompts repeated {REPEAT_MIN_COUNT}+ times this window._"
        )
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
    lines.append("## Optimizations (per-prompt action list)")
    lines.append("")
    if top_tunable:
        lines.append(
            "Top-5 highest-tunability prompts with the suggested action. "
            "Pick from the top — each carries an explicit reason code that "
            "maps to one concrete fix."
        )
        lines.append("")
        for p in top_tunable[:5]:
            if p["tunability_score"] < 10:
                continue  # below noise floor
            text = _truncate(p.get("text", ""), 50)
            lines.append(
                f"> [!tip] **[{p['tunability_score']:.0f}] "
                f"`{p['reason']}`** — `{text}` "
                f"({_fmt(p.get('total_tokens') or 0)} tokens). "
                f"{p['suggested_action']}"
            )
        # Fallback when all scores < noise floor
        if all(p["tunability_score"] < 10 for p in top_tunable[:5]):
            lines.append("> [!tip] Nothing scored above the noise floor — healthy week.")
    else:
        lines.append("> [!tip] No prompts to analyze in this window.")
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


# ----- tunability helpers ------------------------------------------------


def _normalize_prompt_text(text: str) -> str:
    """Normalize for repeat-detection grouping.

    Lowercase, collapse whitespace, strip trailing punctuation, take first
    80 chars. Two prompts that differ only in whitespace / case / trailing
    punctuation hash to the same bucket. Slash-command-only prompts
    (`/sn-foo`, `/clear`) are treated as their own bucket — useful because
    a /clear-heavy session lights up immediately.
    """
    if not text:
        return ""
    s = text.lower().strip()
    s = re.sub(r"\s+", " ", s)
    s = s.rstrip(".!? ,;:")
    return s[:80]


def _compute_repeat_groups(prompts: list[dict]) -> dict[str, int]:
    """Group prompts by normalized prefix; return {normalized_text: count}."""
    groups: dict[str, int] = {}
    for p in prompts:
        key = _normalize_prompt_text(p.get("text", ""))
        if not key:
            continue
        groups[key] = groups.get(key, 0) + 1
    return groups


def _median(values: list[int]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    mid = len(s) // 2
    if len(s) % 2:
        return float(s[mid])
    return (s[mid - 1] + s[mid]) / 2.0


def _cache_hit_pct(p: dict) -> float:
    inp = p.get("input") or {}
    uncached = inp.get("uncached", 0) or 0
    cache_create = inp.get("cache_create", 0) or 0
    cache_read = inp.get("cache_read", 0) or 0
    total_input = uncached + cache_create + cache_read
    if not total_input:
        return 100.0
    return cache_read / total_input * 100.0


def _cache_break_count_for_prompt(p: dict, cache_breaks: list[dict]) -> int:
    """How many cache_break events have this prompt as the 'here:true' context?"""
    target_ts = p.get("ts")
    target_text = p.get("text")
    n = 0
    for cb in cache_breaks:
        for c in cb.get("context") or []:
            if c.get("here") and c.get("ts") == target_ts and c.get("text") == target_text:
                n += 1
                break
    return n


def _determine_reason(
    p: dict,
    cache_hit_pct: float,
    cache_break_count: int,
    repeat_count: int,
    median_api_calls: float,
    output_ratio: float,
) -> str:
    """Priority-ordered reason code for why this prompt is expensive."""
    if repeat_count >= REPEAT_MIN_COUNT:
        return "repeat"
    if (p.get("subagent_calls", 0) or 0) >= 3:
        return "subagent-heavy"
    calls = p.get("api_calls", 0) or 0
    if median_api_calls and calls >= 2 * max(median_api_calls, 1):
        return "loop-thrash"
    if cache_hit_pct < PROMPT_CACHE_TARGET:
        return "cache-miss"
    if cache_break_count >= 1:
        return "cold-start"
    if output_ratio < LOW_OUTPUT_RATIO:
        return "low-output"
    return "expensive"


def _tunability_score(
    p: dict,
    cache_hit_pct: float,
    cache_break_count: int,
    repeat_count: int,
    median_api_calls: float,
) -> float:
    """0-100 composite. Higher = better candidate to tune.

    Weights:
    - 30 max: repeat count (each repeat above the first adds 6, cap 5)
    - 25 max: cache-miss share (lower hit % = more)
    - 20 max: subagent fan-out (each call adds 2, cap 10)
    - 20 max: API-call thrash above median
    -  5 max: cache-break recurrence
    """
    score = 0.0
    # repeats — most actionable signal
    score += min(max(repeat_count - 1, 0), 5) * 6  # max 30
    # cache miss
    miss = max(0.0, 85.0 - cache_hit_pct) / 85.0
    score += miss * 25  # max 25
    # subagent fan-out
    sub_calls = p.get("subagent_calls", 0) or 0
    score += min(sub_calls, 10) * 2  # max 20
    # API-call thrash
    api_calls = p.get("api_calls", 0) or 0
    over = max(0.0, api_calls - max(median_api_calls, 1))
    score += min(over, 20)  # max 20
    # cache-break recurrence
    score += min(cache_break_count, 5)  # max 5
    return min(score, 100.0)


_REASON_TO_ACTION = {
    "repeat": (
        "Promote to a `/sn-<slug>` skill or a CLAUDE.md macro — typed every "
        "session, paid in cache misses each time."
    ),
    "subagent-heavy": (
        "Scope to fewer parallel subagents or pick a smaller model per call; "
        "the orchestrator overhead is dominating."
    ),
    "loop-thrash": (
        "Tighten the plan, lower `max_turns`, or reduce tool-use chains — "
        "many API calls per single user prompt = retry loop."
    ),
    "cache-miss": (
        "System-prompt churn — pin CLAUDE.md before commits, reduce hook "
        "noise, avoid editing settings mid-session."
    ),
    "cold-start": (
        "Cache rebuild penalty — group related work; avoid `/clear` and "
        "compaction mid-task; resume sessions instead of starting fresh."
    ),
    "low-output": (
        "Loaded big context for tiny output — switch to targeted Read/Grep "
        "instead of spraying files into context."
    ),
    "expensive": (
        "Costly but no clear waste signal — split into smaller tasks or "
        "review whether the question scope is right-sized."
    ),
}


def _suggested_action(p: dict, reason: str, repeat_count: int) -> str:
    base = _REASON_TO_ACTION.get(reason, _REASON_TO_ACTION["expensive"])
    if reason == "repeat" and repeat_count >= REPEAT_MIN_COUNT:
        return f"Typed {repeat_count}× this window — {base}"
    return base


def _dedup_by_normalized_text(prompts: list[dict]) -> list[dict]:
    """Collapse augmented prompts that share a normalized text.

    Keeps the highest-scoring instance as the representative row; sums
    `total_tokens` across instances so the table row reflects the full
    spend on that logical intent. Other per-instance fields (api_calls,
    cache_break_count, subagent_calls) are summed as well for a faithful
    rollup.
    """
    groups: dict[str, dict] = {}
    for p in prompts:
        key = _normalize_prompt_text(p.get("text", "")) or p.get("text", "")
        existing = groups.get(key)
        if existing is None:
            groups[key] = dict(p)
            continue
        # Sum per-instance counters
        existing["total_tokens"] = (existing.get("total_tokens", 0) or 0) + (p.get("total_tokens", 0) or 0)
        existing["api_calls"] = (existing.get("api_calls", 0) or 0) + (p.get("api_calls", 0) or 0)
        existing["subagent_calls"] = (existing.get("subagent_calls", 0) or 0) + (p.get("subagent_calls", 0) or 0)
        existing["cache_break_count"] = existing.get("cache_break_count", 0) + p.get("cache_break_count", 0)
        # Keep the worst (lowest) cache-hit % — that's the failure mode
        existing["cache_hit_pct"] = min(existing.get("cache_hit_pct", 100), p.get("cache_hit_pct", 100))
        # Keep highest tunability score so the row sorts to the right place
        if p.get("tunability_score", 0) > existing.get("tunability_score", 0):
            existing["tunability_score"] = p["tunability_score"]
            existing["reason"] = p.get("reason", existing.get("reason"))
            existing["suggested_action"] = p.get("suggested_action", existing.get("suggested_action"))
    return list(groups.values())


def _augment_prompt(
    p: dict,
    cache_breaks: list[dict],
    repeat_groups: dict[str, int],
    median_api_calls: float,
    proj_total: int,
) -> dict:
    """Return a copy of `p` with tunability fields attached."""
    output = p.get("output", 0) or 0
    inp = p.get("input") or {}
    total_input = (inp.get("uncached", 0) or 0) + (inp.get("cache_create", 0) or 0) + (inp.get("cache_read", 0) or 0)
    total = p.get("total_tokens", 0) or (total_input + output)
    output_ratio = (output / total) if total else 0.0

    cache_hit = _cache_hit_pct(p)
    cb_count = _cache_break_count_for_prompt(p, cache_breaks)
    norm_text = _normalize_prompt_text(p.get("text", ""))
    repeat_count = repeat_groups.get(norm_text, 1)

    reason = _determine_reason(
        p, cache_hit, cb_count, repeat_count, median_api_calls, output_ratio,
    )
    score = _tunability_score(p, cache_hit, cb_count, repeat_count, median_api_calls)
    action = _suggested_action(p, reason, repeat_count)

    return {
        **p,
        "cache_hit_pct": cache_hit,
        "cache_break_count": cb_count,
        "repeat_count": repeat_count,
        "reason": reason,
        "tunability_score": score,
        "suggested_action": action,
    }


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
