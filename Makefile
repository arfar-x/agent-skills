.PHONY: help install-skill-deps skill-vendored-add skill-vendored-update skill-vendored-delete

# Interpreter whose environment `install-skill-deps` installs into -- the one
# your agent runs `python3 scripts/...` with. Not needed with `uv run`.
PYTHON ?= python3
# Space-separated skills directories to scan instead of `npx skills ls`.
SKILLS_DIR ?=
# Extra pip arguments, e.g. PIP_ARGS=--user.
PIP_ARGS ?=

help:
	@echo "Skill dependencies (see README.md's 'Python dependencies' section):"
	@echo "  make install-skill-deps [PYTHON=python3] [SKILLS_DIR=dir ...] [PIP_ARGS=...] [DRY_RUN=1]"
	@echo ""
	@echo "Vendored-skill management (see README.md's 'Vendored skills' section):"
	@echo "  make skill-vendored-add    <github-tree-url>"
	@echo "  make skill-vendored-update <github-tree-url|skill-name>"
	@echo "  make skill-vendored-delete <skill-name>"
	@echo ""
	@echo "Example:"
	@echo "  make skill-vendored-add https://github.com/affaan-m/ECC/tree/main/.agents/skills/strategic-compact"
	@echo "  make skill-vendored-update strategic-compact"
	@echo "  make skill-vendored-delete strategic-compact"

install-skill-deps:
	@scripts/install_skill_deps.py --python "$(PYTHON)" \
		$(foreach d,$(SKILLS_DIR),--skills-dir "$(d)") \
		$(if $(DRY_RUN),--dry-run) \
		$(if $(strip $(PIP_ARGS)),-- $(PIP_ARGS))

skill-vendored-add:
	@scripts/vendor_skill.sh add $(filter-out $@,$(MAKECMDGOALS))

skill-vendored-update:
	@scripts/vendor_skill.sh update $(filter-out $@,$(MAKECMDGOALS))

skill-vendored-delete:
	@scripts/vendor_skill.sh delete $(filter-out $@,$(MAKECMDGOALS))

# Swallows the extra positional argument (a URL or skill name) passed after
# the target above, so Make doesn't try to build it as a target of its own.
%:
	@:
