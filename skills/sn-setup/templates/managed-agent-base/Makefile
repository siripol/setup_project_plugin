# Use bash so recipes can rely on `$((10#$VAR + 1))` arithmetic, $${VAR:-default}
# parameter expansion, etc. POSIX sh (dash on Ubuntu) does not support either.
SHELL := /bin/bash

.PHONY: help agent session test fmt lint validate logs-tail logs-clean logs-stats mcp-server \
        claude-local-edit claude-local-show \
        req-new req-import req-rollback req-resume req-replay req-loop \
        sprint-new sprint-add sprint-remove sprint-run sprint-done sprint-status \
        sprint-concurrent worktree-add worktree-list worktree-remove \
        knowledge-check knowledge-update knowledge-promote knowledge-demote knowledge-tech-matrix \
        gh-import gh-close workflow-status integration-test rate-limit-status check-invariants \
        safety-status safety-reset-rate-limit safety-trip-breaker safety-reset-breaker \
        hooks-install hooks-uninstall orchestrate subagent-index

help: ## Show this help
	@printf "Targets:\n"
	@grep -hE '^[a-zA-Z0-9_-]+:.*## ' $(MAKEFILE_LIST) | sort | \
	 sed 's/^\([^:]*\):.*## /  \1\t/'

agent: ## Apply Managed Agent config (ant agents apply agents/main.yaml)
	ant agents apply agents/main.yaml

session: ## Start a Managed Agent session for $$AGENT_ID
	@if [ -z "$$AGENT_ID" ]; then echo "AGENT_ID env var not set"; exit 1; fi
	ant sessions create --agent-id $$AGENT_ID

validate: ## Validate agents/main.yaml via ant CLI
	ant agents validate agents/main.yaml

logs-tail: ## Tail .sn-init/logs JSONL with jq
	@mkdir -p .sn-init/logs
	@tail -F .sn-init/logs/exec-*.jsonl 2>/dev/null | (command -v jq >/dev/null && jq . || cat)

logs-clean: ## Delete audit logs older than 30 days
	@find .sn-init/logs -name 'exec-*.jsonl' -mtime +30 -delete 2>/dev/null || true

logs-stats: ## Tool + token usage summary per session
	@if ! command -v jq >/dev/null; then echo "jq required"; exit 1; fi
	@for f in .sn-init/logs/exec-*.jsonl; do \
		[ -f "$$f" ] || continue; \
		echo "$$f"; \
		jq -s 'group_by(.tool_name) | map({tool: .[0].tool_name, count: length, in: (map(.usage.input_tokens // 0) | add), out: (map(.usage.output_tokens // 0) | add)})' "$$f"; \
	done

# --- local memory ----------------------------------------------------------

claude-local-edit: ## Append ENTRY=... to CLAUDE.local.md
	@if [ -z "$$ENTRY" ]; then echo "Usage: make claude-local-edit ENTRY=\"...\""; exit 2; fi
	@touch CLAUDE.local.md
	@ts="$$(date +'%Y-%m-%d %H:%M')"; \
	 printf '\n- %s — %s\n' "$$ts" "$$ENTRY" >> CLAUDE.local.md; \
	 echo "appended to CLAUDE.local.md"

claude-local-show: ## Print CLAUDE.local.md
	@if [ -f CLAUDE.local.md ]; then cat CLAUDE.local.md; else echo "(no CLAUDE.local.md yet)"; fi

# --- workflow --------------------------------------------------------------

req-new: ## Scaffold REQ-NNN-<SLUG> from template
	@if [ -z "$$SLUG" ]; then echo "Usage: make req-new SLUG=<slug>"; exit 2; fi
	@mkdir -p docs/requirements/active
	@next="$$(find docs -name 'REQ-*.md' | sed 's/.*REQ-\([0-9]*\).*/\1/' | sort -n | tail -1)"; \
	 next="$$(printf '%03d' $$((10#$${next:-000} + 1)))"; \
	 path="docs/requirements/active/REQ-$$next-$$SLUG.md"; \
	 cp docs/requirements/template.md "$$path"; \
	 sed -i.bak "s/REQ-NNN/REQ-$$next/" "$$path" 2>/dev/null && rm -f "$$path.bak"; \
	 echo "created $$path"

req-import: ## Convert FILE=<path> (md/txt/json/docx/pdf) to a new REQ
	@if [ -z "$$FILE" ]; then echo "Usage: make req-import FILE=<path>"; exit 2; fi
	python3 scripts/req_import.py "$$FILE"

req-rollback: ## Reset to pre-REQ git snapshot for REQ=REQ-NNN
	@if [ -z "$$REQ" ]; then echo "Usage: make req-rollback REQ=REQ-NNN"; exit 2; fi
	@tag="$$(git tag | grep "^sn-init/pre-$$REQ-" | sort -r | head -1)"; \
	 if [ -z "$$tag" ]; then echo "no pre-REQ tag for $$REQ"; exit 2; fi; \
	 git reset --hard "$$tag"

req-resume: ## Resume orchestrator from workflow-state.json
	@echo "Resume cycle from .sn-init/workflow-state.json (orchestrator handles via Claude session)"

req-replay: ## Open replay/REQ-NNN branch for regression check
	@if [ -z "$$REQ" ]; then echo "Usage: make req-replay REQ=REQ-NNN"; exit 2; fi
	@git checkout -b "replay/$$REQ" || git checkout "replay/$$REQ"
	@echo "switched to replay branch; re-run sprint-run to replay"

req-loop: ## Hint: run /sn-sprint-run inside Claude session
	@echo "Invoke /sn-sprint-run for the active sprint to start the spec-loop cycle."

sprint-new: ## Create docs/sprints/active/SPRINT-NNN-<SLUG>/
	@if [ -z "$$SLUG" ]; then echo "Usage: make sprint-new SLUG=<slug>"; exit 2; fi
	@next="$$(find docs/sprints -name 'SPRINT-*' | sed 's/.*SPRINT-\([0-9]*\).*/\1/' | sort -n | tail -1)"; \
	 next="$$(printf '%03d' $$((10#$${next:-000} + 1)))"; \
	 dir="docs/sprints/active/SPRINT-$$next-$$SLUG"; \
	 mkdir -p "$$dir/requirements" "$$dir/exec-plans" "$$dir/tasks" "$$dir/proof"; \
	 cp docs/sprints/template.md "$$dir/sprint.md"; \
	 sed -i.bak "s/SPRINT-NNN/SPRINT-$$next/" "$$dir/sprint.md" 2>/dev/null && rm -f "$$dir/sprint.md.bak"; \
	 echo "created $$dir"

sprint-add: ## Move REQ into SPRINT (SPRINT=... REQ=...)
	@if [ -z "$$SPRINT" ] || [ -z "$$REQ" ]; then echo "Usage: make sprint-add SPRINT=... REQ=..."; exit 2; fi
	@src="$$(find docs/requirements/active -name "$$REQ-*.md" | head -1)"; \
	 dst="$$(find docs/sprints/active -type d -name "$$SPRINT-*" | head -1)/requirements/"; \
	 if [ -z "$$src" ] || [ -z "$$dst" ]; then echo "REQ or SPRINT not found"; exit 2; fi; \
	 mv "$$src" "$$dst"; \
	 echo "moved $$(basename $$src) → $$dst"

sprint-remove: ## Move REQ out of SPRINT back to requirements/active
	@if [ -z "$$SPRINT" ] || [ -z "$$REQ" ]; then echo "Usage: make sprint-remove SPRINT=... REQ=..."; exit 2; fi
	@src="$$(find docs/sprints/active -path "*$$SPRINT*/requirements/$$REQ-*.md" | head -1)"; \
	 if [ -z "$$src" ]; then echo "REQ not found in sprint"; exit 2; fi; \
	 mv "$$src" docs/requirements/active/; \
	 echo "moved back to docs/requirements/active/"

sprint-run: ## Hint: kick off /sn-sprint-run SPRINT=... in Claude
	@if [ -z "$$SPRINT" ]; then echo "Usage: make sprint-run SPRINT=SPRINT-NNN"; exit 2; fi
	@echo "Invoke /sn-sprint-run $$SPRINT in your Claude Code session — the orchestrator runs sn-impact-analyzer → sn-planner → sn-task-* → sn-adversary → sn-evaluator."

sprint-done: ## Archive SPRINT-NNN to docs/sprints/completed/
	@if [ -z "$$SPRINT" ]; then echo "Usage: make sprint-done SPRINT=SPRINT-NNN"; exit 2; fi
	@dir="$$(find docs/sprints/active -type d -name "$$SPRINT-*" | head -1)"; \
	 if [ -z "$$dir" ]; then echo "sprint not found"; exit 2; fi; \
	 mv "$$dir" docs/sprints/completed/; \
	 echo "archived $$SPRINT → docs/sprints/completed/"

sprint-status: ## List active + completed sprints
	@echo "ACTIVE sprints:"; \
	 for d in docs/sprints/active/SPRINT-*; do [ -d "$$d" ] && echo "  $$(basename $$d)"; done; \
	 echo "COMPLETED sprints:"; \
	 for d in docs/sprints/completed/SPRINT-*; do [ -d "$$d" ] && echo "  $$(basename $$d)"; done

knowledge-check: ## Run impact-analyzer for SPRINT
	@if [ -z "$$SPRINT" ]; then echo "Usage: make knowledge-check SPRINT=SPRINT-NNN"; exit 2; fi
	@echo "Invoke /sn-knowledge-check $$SPRINT — sn-impact-analyzer runs without sprint-run side-effects."

knowledge-update: ## Refresh Obsidian knowledge buckets
	@echo "Invoke /sn-knowledge-update — sn-knowledge-curator refreshes Obsidian buckets."

knowledge-promote: ## Promote TOPIC to global/shared
	@if [ -z "$$TOPIC" ]; then echo "Usage: make knowledge-promote TOPIC=<topic>"; exit 2; fi
	@echo "Invoke /sn-knowledge-promote $$TOPIC — moves projects/<p>/$$TOPIC.md → global/shared/."

knowledge-demote: ## Demote TOPIC back to project scope
	@if [ -z "$$TOPIC" ]; then echo "Usage: make knowledge-demote TOPIC=<topic>"; exit 2; fi
	@echo "Invoke /sn-knowledge-demote $$TOPIC — moves global/shared/$$TOPIC.md → projects/<p>/."

knowledge-tech-matrix: ## Regenerate cross-project tech matrix
	@echo "Invoke /sn-knowledge-tech-matrix — regenerates <vault>/knowledge/global/tech/README.md."

gh-import: ## Import GitHub issues labeled `req` as REQ files
	@command -v gh >/dev/null || { echo "gh CLI required"; exit 2; }
	@gh issue list --label req --state open --json number,title,body > /tmp/sn-setup-gh.json && \
	 python3 scripts/req_import.py /tmp/sn-setup-gh.json && rm /tmp/sn-setup-gh.json

gh-close: ## Close GitHub issue (REQ=... PR=...)
	@if [ -z "$$REQ" ] || [ -z "$$PR" ]; then echo "Usage: make gh-close REQ=REQ-NNN PR=<pr-number>"; exit 2; fi
	@command -v gh >/dev/null || { echo "gh CLI required"; exit 2; }
	@issue="$$(echo $$REQ | sed -E 's/REQ-0*([0-9]+).*/\1/')"; \
	 gh issue close "$$issue" --comment "Closed by PR #$$PR (sn-setup spec-loop)." && \
	 echo "closed GitHub issue $$issue"

# --- worktree concurrency ---

worktree-add: ## Add a worktree for REQ
	@if [ -z "$$REQ" ]; then echo "Usage: make worktree-add REQ=REQ-NNN"; exit 2; fi
	@mkdir -p .sn-init/worktrees
	@branch="req/$$REQ"; \
	 git worktree add ".sn-init/worktrees/$$REQ" -b "$$branch" 2>/dev/null || \
	   git worktree add ".sn-init/worktrees/$$REQ" "$$branch"; \
	 echo "worktree → .sn-init/worktrees/$$REQ (branch $$branch)"

worktree-list: ## List git worktrees
	@git worktree list

worktree-remove: ## Remove worktree for REQ
	@if [ -z "$$REQ" ]; then echo "Usage: make worktree-remove REQ=REQ-NNN"; exit 2; fi
	@git worktree remove ".sn-init/worktrees/$$REQ" --force 2>/dev/null && \
	  echo "removed worktree for $$REQ" || echo "no worktree for $$REQ"

sprint-concurrent: ## Hint: run /sn-sprint-run with --workflow-concurrent=N
	@if [ -z "$$SPRINT" ] || [ -z "$$N" ]; then echo "Usage: make sprint-concurrent SPRINT=SPRINT-NNN N=3"; exit 2; fi
	@echo "Invoke /sn-sprint-run $$SPRINT with --workflow-concurrent=$$N — orchestrator spawns N worktrees."

# --- safety status ---

safety-status: ## Print rate-limit + circuit breaker state
	@python3 scripts/safety.py status 2>/dev/null || echo "(scripts/safety.py not available)"

safety-reset-rate-limit: ## Reset the hourly rate window
	@python3 scripts/safety.py reset-rate-limit

safety-trip-breaker: ## Force circuit breaker to tripped for REQ
	@if [ -z "$$REQ" ]; then echo "Usage: make safety-trip-breaker REQ=REQ-NNN"; exit 2; fi
	@python3 scripts/safety.py trip-breaker $$REQ

safety-reset-breaker: ## Reset circuit breaker for REQ
	@if [ -z "$$REQ" ]; then echo "Usage: make safety-reset-breaker REQ=REQ-NNN"; exit 2; fi
	@python3 scripts/safety.py reset-breaker $$REQ

workflow-status: ## Show active REQs + sprints
	@echo "Active REQs (unassigned):"; \
	 ls docs/requirements/active/ 2>/dev/null | head -10; \
	 echo "Active sprints:"; \
	 ls docs/sprints/active/ 2>/dev/null | head -10

integration-test: ## Alias for `make test`
	@$$(MAKE) test

rate-limit-status: ## Show this hour's call/token usage
	@if [ -f .sn-init/workflow-state.json ]; then \
	   python3 -c "import json; s=json.load(open('.sn-init/workflow-state.json')); print(s.get('rate_window', {}))"; \
	 else echo "(no workflow-state.json yet)"; fi

check-invariants: ## List harness invariants (lang test runs them)
	@find .harness/invariants -name '*.md' | xargs -I {} echo "check {}"
	@echo "Run lang-specific test target to execute paired invariant tests."

subagent-index: ## Regenerate docs/design-docs/subagents.md
	@python3 scripts/gen_subagent_index.py

# --- git hooks ---

hooks-install: ## Point git at .githooks/
	@git config core.hooksPath .githooks && \
	 chmod +x .githooks/* 2>/dev/null; \
	 echo "git hooks → .githooks/"

hooks-uninstall: ## Reset git hooks to default
	@git config --unset core.hooksPath || true; \
	 echo "git hooks reset to default"

# --- orchestrator wrapper ---

orchestrate: ## Run spec-loop orchestrator for SPRINT=...
	@if [ -z "$$SPRINT" ]; then echo "Usage: make orchestrate SPRINT=SPRINT-NNN"; exit 2; fi
	@if [ -f src/orchestrator.py ] || [ -f src/orchestrator.ts ] || [ -f src/cmd/orchestrator/main.go ]; then \
	   $(MAKE) orchestrator-run SPRINT=$$SPRINT; \
	 else \
	   python3 scripts/orchestrator.py run $$SPRINT; \
	 fi

# Lang-specific targets live in Makefile.<lang> (e.g. Makefile.go) and are merged here.
-include Makefile.*
