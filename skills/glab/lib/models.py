"""Normalizers turning raw GitLab payloads into small JSON-safe dicts.

The agent never sees GitLab's raw REST payloads, only these structures.
Every one that has a page on the web includes ``web_url`` so results can
be linked without constructing URLs.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

from .utils import safe_get


def user(u: Mapping[str, Any]) -> Dict[str, Any]:
    return {"id": u.get("id"), "username": u.get("username"), "name": u.get("name"), "web_url": u.get("web_url")}


def project(p: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "id": p.get("id"),
        "path_with_namespace": p.get("path_with_namespace"),
        "name": p.get("name"),
        "description": p.get("description"),
        "default_branch": p.get("default_branch"),
        "visibility": p.get("visibility"),
        "web_url": p.get("web_url"),
        "last_activity_at": p.get("last_activity_at"),
    }


def branch(b: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "name": b.get("name"),
        "default": b.get("default"),
        "protected": b.get("protected"),
        "commit_sha": safe_get(b, "commit", "id"),
        "web_url": b.get("web_url"),
    }


def tree_entry(e: Mapping[str, Any]) -> Dict[str, Any]:
    return {"path": e.get("path"), "name": e.get("name"), "type": e.get("type")}


def mr_summary(m: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "iid": m.get("iid"),
        "project_id": m.get("project_id"),
        "title": m.get("title"),
        "state": m.get("state"),
        "draft": m.get("draft", m.get("work_in_progress")),
        "author": safe_get(m, "author", "username"),
        "source_branch": m.get("source_branch"),
        "target_branch": m.get("target_branch"),
        "updated_at": m.get("updated_at"),
        "web_url": m.get("web_url"),
    }


def mr_detail(m: Mapping[str, Any]) -> Dict[str, Any]:
    out = mr_summary(m)
    out.update(
        {
            "description": m.get("description"),
            "created_at": m.get("created_at"),
            "reviewers": [r.get("username") for r in m.get("reviewers") or []],
            "assignees": [a.get("username") for a in m.get("assignees") or []],
            "labels": m.get("labels") or [],
            "merge_status": m.get("detailed_merge_status") or m.get("merge_status"),
            "sha": m.get("sha"),
            "diff_refs": m.get("diff_refs"),
            "changes_count": m.get("changes_count"),
        }
    )
    return out


def file_diff(d: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "old_path": d.get("old_path"),
        "new_path": d.get("new_path"),
        "new_file": d.get("new_file"),
        "renamed_file": d.get("renamed_file"),
        "deleted_file": d.get("deleted_file"),
        "diff": d.get("diff"),
    }


def note(n: Mapping[str, Any]) -> Dict[str, Any]:
    pos = n.get("position") or None
    return {
        "id": n.get("id"),
        "author": safe_get(n, "author", "username"),
        "body": n.get("body"),
        "created_at": n.get("created_at"),
        "system": n.get("system"),
        "resolvable": n.get("resolvable"),
        "resolved": n.get("resolved"),
        "position": (
            {k: pos.get(k) for k in ("new_path", "old_path", "new_line", "old_line")} if pos else None
        ),
    }


def discussion(d: Mapping[str, Any]) -> Dict[str, Any]:
    notes: List[Dict[str, Any]] = [note(n) for n in d.get("notes") or []]
    return {"id": d.get("id"), "individual_note": d.get("individual_note"), "notes": notes}
