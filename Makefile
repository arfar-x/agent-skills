.PHONY: help skill-vendored-add skill-vendored-update skill-vendored-delete

help:
	@echo "Vendored-skill management (see README.md's 'Vendored skills' section):"
	@echo "  make skill-vendored-add    <github-tree-url>"
	@echo "  make skill-vendored-update <github-tree-url|skill-name>"
	@echo "  make skill-vendored-delete <skill-name>"
	@echo ""
	@echo "Example:"
	@echo "  make skill-vendored-add https://github.com/affaan-m/ECC/tree/main/.agents/skills/strategic-compact"
	@echo "  make skill-vendored-update strategic-compact"
	@echo "  make skill-vendored-delete strategic-compact"

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
