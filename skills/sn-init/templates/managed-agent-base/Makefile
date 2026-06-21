.PHONY: help agent session test fmt lint validate logs-tail logs-clean logs-stats mcp-server \
        claude-local-edit claude-local-show \
        req-new req-import req-rollback req-resume req-replay req-loop \
        sprint-new sprint-add sprint-remove sprint-run sprint-done sprint-status \
        knowledge-check knowledge-update knowledge-promote knowledge-demote knowledge-tech-matrix \
        gh-import workflow-status integration-test rate-limit-status check-invariants

help:
	@echo "make agent      — ant agents apply agents/main.yaml"
	@echo "make session    — ant sessions create --agent-id $$AGENT_ID"
	@echo "make test       — lang test suite"
	@echo "make fmt        — format"
	@echo "make lint       — lint"
	@echo "make validate   — ant agents validate"
	@echo "make logs-tail  — tail audit log"
	@echo "make logs-clean — delete audit logs older than 30 days"
	@echo "make logs-stats — count tool calls + token usage per session"
	@echo "make mcp-server — start project-local MCP server"

agent:
	ant agents apply agents/main.yaml

session:
	@if [ -z "$$AGENT_ID" ]; then echo "AGENT_ID env var not set"; exit 1; fi
	ant sessions create --agent-id $$AGENT_ID

validate:
	ant agents validate agents/main.yaml

logs-tail:
	@mkdir -p .sn-init/logs
	@tail -F .sn-init/logs/exec-*.jsonl 2>/dev/null | (command -v jq >/dev/null && jq . || cat)

logs-clean:
	@find .sn-init/logs -name 'exec-*.jsonl' -mtime +30 -delete 2>/dev/null || true

logs-stats:
	@if ! command -v jq >/dev/null; then echo "jq required"; exit 1; fi
	@for f in .sn-init/logs/exec-*.jsonl; do \
		[ -f "$$f" ] || continue; \
		echo "$$f"; \
		jq -s 'group_by(.tool_name) | map({tool: .[0].tool_name, count: length, in: (map(.usage.input_tokens // 0) | add), out: (map(.usage.output_tokens // 0) | add)})' "$$f"; \
	done

# --- local memory ----------------------------------------------------------

claude-local-edit:
	@if [ -z "$$ENTRY" ]; then echo "Usage: make claude-local-edit ENTRY=\"...\""; exit 2; fi
	@touch CLAUDE.local.md
	@ts="$$(date +'%Y-%m-%d %H:%M')"; \
	 printf '\n- %s — %s\n' "$$ts" "$$ENTRY" >> CLAUDE.local.md; \
	 echo "appended to CLAUDE.local.md"

claude-local-show:
	@if [ -f CLAUDE.local.md ]; then cat CLAUDE.local.md; else echo "(no CLAUDE.local.md yet)"; fi

# --- workflow --------------------------------------------------------------

req-new:
	@if [ -z "$$SLUG" ]; then echo "Usage: make req-new SLUG=<slug>"; exit 2; fi
	@mkdir -p docs/requirements/active
	@next="$$(find docs -name 'REQ-*.md' | sed 's/.*REQ-\([0-9]*\).*/\1/' | sort -n | tail -1)"; \
	 next="$$(printf '%03d' $$((10#$${next:-000} + 1)))"; \
	 path="docs/requirements/active/REQ-$$next-$$SLUG.md"; \
	 cp docs/requirements/template.md "$$path"; \
	 sed -i.bak "s/REQ-NNN/REQ-$$next/" "$$path" 2>/dev/null && rm -f "$$path.bak"; \
	 echo "created $$path"

req-import:
	@if [ -z "$$FILE" ]; then echo "Usage: make req-import FILE=<path>"; exit 2; fi
	python3 scripts/req_import.py "$$FILE"

req-rollback:
	@if [ -z "$$REQ" ]; then echo "Usage: make req-rollback REQ=REQ-NNN"; exit 2; fi
	@tag="$$(git tag | grep "^sn-init/pre-$$REQ-" | sort -r | head -1)"; \
	 if [ -z "$$tag" ]; then echo "no pre-REQ tag for $$REQ"; exit 2; fi; \
	 git reset --hard "$$tag"

req-resume:
	@echo "Resume cycle from .sn-init/workflow-state.json (orchestrator handles via Claude session)"

req-replay:
	@if [ -z "$$REQ" ]; then echo "Usage: make req-replay REQ=REQ-NNN"; exit 2; fi
	@git checkout -b "replay/$$REQ" || git checkout "replay/$$REQ"
	@echo "switched to replay branch; re-run sprint-run to replay"

req-loop:
	@echo "Invoke /sprint-run for the active sprint to start the spec-loop cycle."

sprint-new:
	@if [ -z "$$SLUG" ]; then echo "Usage: make sprint-new SLUG=<slug>"; exit 2; fi
	@next="$$(find docs/sprints -name 'SPRINT-*' | sed 's/.*SPRINT-\([0-9]*\).*/\1/' | sort -n | tail -1)"; \
	 next="$$(printf '%03d' $$((10#$${next:-000} + 1)))"; \
	 dir="docs/sprints/active/SPRINT-$$next-$$SLUG"; \
	 mkdir -p "$$dir/requirements" "$$dir/exec-plans" "$$dir/tasks" "$$dir/proof"; \
	 cp docs/sprints/template.md "$$dir/sprint.md"; \
	 sed -i.bak "s/SPRINT-NNN/SPRINT-$$next/" "$$dir/sprint.md" 2>/dev/null && rm -f "$$dir/sprint.md.bak"; \
	 echo "created $$dir"

sprint-add:
	@if [ -z "$$SPRINT" ] || [ -z "$$REQ" ]; then echo "Usage: make sprint-add SPRINT=... REQ=..."; exit 2; fi
	@src="$$(find docs/requirements/active -name "$$REQ-*.md" | head -1)"; \
	 dst="$$(find docs/sprints/active -type d -name "$$SPRINT-*" | head -1)/requirements/"; \
	 if [ -z "$$src" ] || [ -z "$$dst" ]; then echo "REQ or SPRINT not found"; exit 2; fi; \
	 mv "$$src" "$$dst"; \
	 echo "moved $$(basename $$src) → $$dst"

sprint-remove:
	@if [ -z "$$SPRINT" ] || [ -z "$$REQ" ]; then echo "Usage: make sprint-remove SPRINT=... REQ=..."; exit 2; fi
	@src="$$(find docs/sprints/active -path "*$$SPRINT*/requirements/$$REQ-*.md" | head -1)"; \
	 if [ -z "$$src" ]; then echo "REQ not found in sprint"; exit 2; fi; \
	 mv "$$src" docs/requirements/active/; \
	 echo "moved back to docs/requirements/active/"

sprint-run:
	@if [ -z "$$SPRINT" ]; then echo "Usage: make sprint-run SPRINT=SPRINT-NNN"; exit 2; fi
	@echo "Invoke /sprint-run $$SPRINT in your Claude Code session — the orchestrator runs impact-analyzer → planner → tasks → tester → adversary → evaluator."

sprint-done:
	@if [ -z "$$SPRINT" ]; then echo "Usage: make sprint-done SPRINT=SPRINT-NNN"; exit 2; fi
	@dir="$$(find docs/sprints/active -type d -name "$$SPRINT-*" | head -1)"; \
	 if [ -z "$$dir" ]; then echo "sprint not found"; exit 2; fi; \
	 mv "$$dir" docs/sprints/completed/; \
	 echo "archived $$SPRINT → docs/sprints/completed/"

sprint-status:
	@echo "ACTIVE sprints:"; \
	 for d in docs/sprints/active/SPRINT-*; do [ -d "$$d" ] && echo "  $$(basename $$d)"; done; \
	 echo "COMPLETED sprints:"; \
	 for d in docs/sprints/completed/SPRINT-*; do [ -d "$$d" ] && echo "  $$(basename $$d)"; done

knowledge-check:
	@if [ -z "$$SPRINT" ]; then echo "Usage: make knowledge-check SPRINT=SPRINT-NNN"; exit 2; fi
	@echo "Invoke /knowledge-check $$SPRINT — impact-analyzer runs without sprint-run side-effects."

knowledge-update:
	@echo "Invoke /knowledge-update — knowledge-curator refreshes Obsidian buckets."

knowledge-promote:
	@if [ -z "$$TOPIC" ]; then echo "Usage: make knowledge-promote TOPIC=<topic>"; exit 2; fi
	@echo "Invoke /knowledge-promote $$TOPIC — moves projects/<p>/$$TOPIC.md → global/shared/."

knowledge-demote:
	@if [ -z "$$TOPIC" ]; then echo "Usage: make knowledge-demote TOPIC=<topic>"; exit 2; fi
	@echo "Invoke /knowledge-demote $$TOPIC — moves global/shared/$$TOPIC.md → projects/<p>/."

knowledge-tech-matrix:
	@echo "Invoke /knowledge-tech-matrix — regenerates <vault>/knowledge/global/tech/README.md."

gh-import:
	@command -v gh >/dev/null || { echo "gh CLI required"; exit 2; }
	@gh issue list --label req --state open --json number,title,body > /tmp/sn-init-gh.json && \
	 python3 scripts/req_import.py /tmp/sn-init-gh.json && rm /tmp/sn-init-gh.json

workflow-status:
	@echo "Active REQs (unassigned):"; \
	 ls docs/requirements/active/ 2>/dev/null | head -10; \
	 echo "Active sprints:"; \
	 ls docs/sprints/active/ 2>/dev/null | head -10

integration-test:
	@$$(MAKE) test

rate-limit-status:
	@if [ -f .sn-init/workflow-state.json ]; then \
	   python3 -c "import json; s=json.load(open('.sn-init/workflow-state.json')); print(s.get('rate_window', {}))"; \
	 else echo "(no workflow-state.json yet)"; fi

check-invariants:
	@find .harness/invariants -name '*.md' | xargs -I {} echo "check {}"
	@echo "Run lang-specific test target to execute paired invariant tests."

# Lang-specific targets live in Makefile.<lang> (e.g. Makefile.go) and are merged here.
-include Makefile.*
