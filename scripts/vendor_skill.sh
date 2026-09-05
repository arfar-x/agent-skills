#!/usr/bin/env bash
# Add, update, or delete a vendored skill -- a skills/<name>/ directory
# imported from one subdirectory of a third-party repo via git subtree,
# pinned to an exact upstream commit. See README.md's "Vendored skills"
# section for the full explanation of why this needs more than a plain
# `git subtree add`. Driven by the top-level Makefile; not meant to be
# run directly except for debugging.
#
# Usage:
#   scripts/vendor_skill.sh add    <github-tree-url>
#   scripts/vendor_skill.sh update <github-tree-url|skill-name>
#   scripts/vendor_skill.sh delete <skill-name>
#
# <github-tree-url> looks like:
#   https://github.com/<owner>/<repo>/tree/<ref>/<path/to/skill>
#
# Every add/update ends in a real commit (git subtree fundamentally works
# by committing, there's no stage-only mode) plus a small follow-up
# commit updating .vendored-skills.json. Nothing here ever pushes.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

MANIFEST="$REPO_ROOT/.vendored-skills.json"
FILTER_REPO_VERSION="v2.47.0"
FILTER_REPO_CACHE="$REPO_ROOT/.cache/tools/git-filter-repo-${FILTER_REPO_VERSION}"

usage() {
	cat >&2 <<'EOF'
Usage:
  scripts/vendor_skill.sh add    <github-tree-url>
  scripts/vendor_skill.sh update <github-tree-url|skill-name>
  scripts/vendor_skill.sh delete <skill-name>
EOF
	exit 1
}

log() { echo "==> $*" >&2; }

# Resolves a usable `git filter-repo` invocation into $FILTER_REPO_CMD (an
# array), preferring one already on PATH; otherwise downloads the single-file
# script git itself recommends (pinned to $FILTER_REPO_VERSION) into a
# gitignored local cache, so a fresh checkout needs no manual setup step.
ensure_filter_repo() {
	if command -v git-filter-repo >/dev/null 2>&1; then
		FILTER_REPO_CMD=(git-filter-repo)
		return
	fi
	if [ ! -x "$FILTER_REPO_CACHE" ]; then
		log "git-filter-repo not found; downloading pinned $FILTER_REPO_VERSION (one-time, cached under .cache/tools/)"
		mkdir -p "$(dirname "$FILTER_REPO_CACHE")"
		curl -sL "https://raw.githubusercontent.com/newren/git-filter-repo/${FILTER_REPO_VERSION}/git-filter-repo" \
			-o "$FILTER_REPO_CACHE"
		chmod +x "$FILTER_REPO_CACHE"
	fi
	FILTER_REPO_CMD=(python3 "$FILTER_REPO_CACHE")
}

# Parses a GitHub tree URL into PARSED_OWNER/PARSED_REPO/PARSED_REF/PARSED_PATH/PARSED_NAME.
# Does not support a ref containing "/" (e.g. "feature/x") -- GitHub's own
# tree URL is itself ambiguous there without querying the API to disambiguate
# ref from path; stick to a plain branch/tag name.
parse_github_tree_url() {
	local url="$1"
	if [[ "$url" =~ ^https://github\.com/([^/]+)/([^/]+)/tree/([^/]+)/(.+)$ ]]; then
		PARSED_OWNER="${BASH_REMATCH[1]}"
		PARSED_REPO="${BASH_REMATCH[2]%.git}"
		PARSED_REF="${BASH_REMATCH[3]}"
		PARSED_PATH="${BASH_REMATCH[4]%/}"
		PARSED_NAME="$(basename "$PARSED_PATH")"
	else
		echo "error: not a GitHub tree URL: $url" >&2
		echo "expected: https://github.com/<owner>/<repo>/tree/<ref>/<path/to/skill>" >&2
		exit 1
	fi
}

manifest_get() { # manifest_get <name> <field> -- prints value, exits 1 if name unknown
	python3 - "$MANIFEST" "$1" "$2" <<'EOF'
import json, sys
path, name, field = sys.argv[1:4]
try:
    data = json.load(open(path))
except FileNotFoundError:
    sys.exit(1)
entry = data.get(name)
if entry is None:
    sys.exit(1)
print(entry.get(field, ""))
EOF
}

manifest_set() { # manifest_set <name> <repo> <ref> <path> <commit>
	python3 - "$MANIFEST" "$1" "$2" "$3" "$4" "$5" <<'EOF'
import json, os, sys
path, name, repo, ref, subpath, commit = sys.argv[1:7]
data = {}
if os.path.exists(path):
    data = json.load(open(path))
data[name] = {"repo": repo, "ref": ref, "path": subpath, "commit": commit}
with open(path, "w") as f:
    json.dump(data, f, indent=2, sort_keys=True)
    f.write("\n")
EOF
}

manifest_delete() { # manifest_delete <name>
	python3 - "$MANIFEST" "$1" <<'EOF'
import json, os, sys
path, name = sys.argv[1:3]
if os.path.exists(path):
    data = json.load(open(path))
    data.pop(name, None)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")
EOF
}

# Does the actual import/resync: filters a scratch bare clone of
# <repo_url>@<ref> down to just <path> via git-filter-repo, then subtree
# add/merges the result into skills/<name>. <mode> is "add" or "update".
#
# Deliberately never fetches <repo_url> into *this* repo directly (no
# `git remote add` + `git fetch`, even though that reads simpler) -- doing
# that would pull every blob reachable from <ref> across the *entire*
# source repo into agent-skills' own .git, exactly what vendoring one
# subdirectory is supposed to avoid. Everything foreign-repo-shaped stays
# confined to the disposable scratch clone below.
do_import() {
	local mode="$1" name="$2" repo_url="$3" ref="$4" path="$5"
	local dest="skills/${name}"

	if [ "$mode" = "add" ] && [ -e "$dest" ]; then
		echo "error: $dest already exists -- use 'make skill-vendored-update $name' instead" >&2
		exit 1
	fi
	if [ "$mode" = "update" ] && [ ! -e "$dest" ]; then
		echo "error: $dest doesn't exist yet -- use 'make skill-vendored-add' instead" >&2
		exit 1
	fi

	ensure_filter_repo

	local scratch
	scratch="$(mktemp -d)"
	trap 'rm -rf "$scratch"' RETURN

	log "Cloning a scratch copy to filter down to $path (this fetches the whole $ref branch -- git-filter-repo's fast-export/fast-import rewrite doesn't reliably trigger partial-clone lazy blob fetches, so --filter=blob:none isn't safe to use here even though it'd be faster)..."
	git clone --quiet --bare --single-branch --branch "$ref" "$repo_url" "$scratch/source.git"

	# Capture the real, dereferenceable upstream commit *before*
	# git-filter-repo rewrites anything -- filter-repo produces new commit
	# objects (different hashes) for the filtered history, since it's
	# genuinely a different tree (renamed paths, dropped commits). Reading
	# HEAD after filtering would record a hash that only ever exists in
	# this disposable scratch clone, not one you could look up on GitHub.
	local upstream_commit
	upstream_commit="$(git --git-dir="$scratch/source.git" rev-parse HEAD)"

	log "Filtering to just $path via git-filter-repo..."
	(cd "$scratch/source.git" && "${FILTER_REPO_CMD[@]}" --force --path "$path" --path-rename "${path}/:")

	local previous_commit
	previous_commit="$(manifest_get "$name" commit 2>/dev/null || true)"

	log "Pulling filtered history into $dest..."
	git fetch --quiet "$scratch/source.git" HEAD

	# Multi-line, so `git log -- skills/<name>` alone tells the whole
	# provenance story without needing to cross-reference the manifest.
	local msg verb
	if [ "$mode" = "add" ]; then
		verb="import"
	else
		verb="update"
	fi
	msg="$(printf 'vendor(%s): %s from %s via git subtree\n\nRepo:   %s\nRef:    %s\nPath:   %s\nCommit: %s\nDest:   %s' \
		"$name" "$verb" "$repo_url" "$repo_url" "$ref" "$path" "$upstream_commit" "$dest")"
	if [ "$mode" = "update" ] && [ -n "$previous_commit" ] && [ "$previous_commit" != "$upstream_commit" ]; then
		msg="${msg}
Previous: ${previous_commit}"
	fi

	# Deliberately not --squash: a squashed import embeds a
	# "git-subtree-split:" trailer recording the exact upstream commit it
	# came from, and every later --squash merge needs that commit object
	# to still exist locally to diff against. Since each sync here starts
	# from a disposable scratch clone that gets deleted right after (and
	# this repo's .git gets gc'd), that object won't reliably still be
	# around next time -- --squash merges are not safe against this
	# workflow's own cleanup. Without --squash, each upstream commit
	# becomes a real local commit instead (richer log, no bookkeeping to
	# lose); the commit message above still names the exact pinned commit
	# either way.
	if [ "$mode" = "add" ]; then
		git subtree add --prefix="$dest" FETCH_HEAD -m "$msg"
	else
		git subtree merge --prefix="$dest" FETCH_HEAD -m "$msg"
	fi

	manifest_set "$name" "$repo_url" "$ref" "$path" "$upstream_commit"
	git add "$MANIFEST"
	if ! git diff --cached --quiet -- "$MANIFEST"; then
		git commit --quiet -m "chore(${name}): update vendor manifest" \
			-m "Commit: ${upstream_commit}" -m "Dest:   ${dest}"
	fi

	log "Done. $dest is now pinned to upstream commit $upstream_commit."
	log "Remember: README.md's 'Skills in this repo' table and 'Vendored skills' section aren't auto-updated -- update them by hand if this is a new skill."
}

cmd="${1:-}"
case "$cmd" in
add)
	url="${2:-}"
	[ -n "$url" ] || usage
	parse_github_tree_url "$url"
	do_import add "$PARSED_NAME" "https://github.com/${PARSED_OWNER}/${PARSED_REPO}.git" "$PARSED_REF" "$PARSED_PATH"
	;;
update)
	arg="${2:-}"
	[ -n "$arg" ] || usage
	if [[ "$arg" =~ ^https:// ]]; then
		parse_github_tree_url "$arg"
		do_import update "$PARSED_NAME" "https://github.com/${PARSED_OWNER}/${PARSED_REPO}.git" "$PARSED_REF" "$PARSED_PATH"
	else
		name="$arg"
		repo="$(manifest_get "$name" repo)" ||
			{ echo "error: '$name' isn't a known vendored skill (check .vendored-skills.json)" >&2; exit 1; }
		ref="$(manifest_get "$name" ref)"
		path="$(manifest_get "$name" path)"
		do_import update "$name" "$repo" "$ref" "$path"
	fi
	;;
delete)
	name="${2:-}"
	[ -n "$name" ] || usage
	dest="skills/${name}"
	[ -e "$dest" ] || { echo "error: $dest doesn't exist" >&2; exit 1; }
	repo="$(manifest_get "$name" repo 2>/dev/null || echo "(unknown -- not in .vendored-skills.json)")"
	ref="$(manifest_get "$name" ref 2>/dev/null || echo "?")"
	path="$(manifest_get "$name" path 2>/dev/null || echo "?")"
	commit="$(manifest_get "$name" commit 2>/dev/null || echo "?")"
	git rm -r --quiet "$dest"
	manifest_delete "$name"
	git add "$MANIFEST"
	msg="$(printf "chore: remove vendored skill '%s'\n\nWas tracking:\nRepo:   %s\nRef:    %s\nPath:   %s\nCommit: %s\nDest:   %s" \
		"$name" "$repo" "$ref" "$path" "$commit" "$dest")"
	git commit --quiet -m "$msg"
	log "Removed $dest."
	log "Remember: README.md's 'Skills in this repo' table and 'Vendored skills' section aren't auto-updated -- remove its row by hand."
	;;
*)
	usage
	;;
esac
