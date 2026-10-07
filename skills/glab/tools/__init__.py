"""Thin, agent-facing entry points.

Every module here does exactly three things: validate input, call the
shared :class:`~lib.glab_client.GitLabClient`, and return structured
JSON. None of them summarize, explain, or reason -- that is the
agent's job.
"""
