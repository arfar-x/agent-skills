from lib.registry import discover_skills, load_subcommands, resolve_include_internal


def test_jira_classified_as_toolset_root(tmp_repo):
    manifests = {m.name: m for m in discover_skills(tmp_repo, include_internal=False)}
    assert manifests["jira"].kind == "toolset_root"
    assert manifests["jira"].script_path == tmp_repo / "skills" / "jira" / "scripts" / "jira_tool.py"
    assert manifests["jira"].toolset == "jira"


def test_jira_worklog_classified_as_thin_wrapper_of_jira(tmp_repo):
    manifests = {m.name: m for m in discover_skills(tmp_repo, include_internal=False)}
    assert manifests["jira-worklog"].kind == "toolset_thin_wrapper"
    assert manifests["jira-worklog"].toolset == "jira"


def test_mood_classified_as_standalone(tmp_repo):
    manifests = {m.name: m for m in discover_skills(tmp_repo, include_internal=False)}
    assert manifests["mood"].kind == "standalone"
    assert manifests["mood"].toolset is None
    assert manifests["mood"].script_path is None


def test_telegram_excluded_by_default(tmp_repo):
    manifests = discover_skills(tmp_repo, include_internal=False)
    assert "telegram" not in {m.name for m in manifests}


def test_telegram_included_when_internal_enabled(tmp_repo):
    manifests = discover_skills(tmp_repo, include_internal=True)
    names = {m.name for m in manifests}
    assert "telegram" in names
    telegram = next(m for m in manifests if m.name == "telegram")
    assert telegram.kind == "toolset_root"
    assert telegram.internal is True


def test_required_environment_variables_preserved(tmp_repo):
    manifests = {m.name: m for m in discover_skills(tmp_repo, include_internal=False)}
    names = {v["name"] for v in manifests["jira"].required_environment_variables}
    assert names == {"JIRA_BASE_URL", "JIRA_DEFAULT_PROJECT"}


def test_load_subcommands_introspects_the_synthetic_toolset(tmp_repo):
    manifests = {m.name: m for m in discover_skills(tmp_repo, include_internal=False)}
    specs = load_subcommands(manifests["jira"])
    assert [s.name for s in specs] == ["now"]


def test_resolve_include_internal_flag_wins(monkeypatch):
    monkeypatch.setenv("INSTALL_INTERNAL_SKILLS", "0")
    assert resolve_include_internal(True) is True


def test_resolve_include_internal_falls_back_to_env(monkeypatch):
    monkeypatch.setenv("INSTALL_INTERNAL_SKILLS", "1")
    assert resolve_include_internal(False) is True


def test_resolve_include_internal_defaults_false(monkeypatch):
    monkeypatch.delenv("INSTALL_INTERNAL_SKILLS", raising=False)
    assert resolve_include_internal(False) is False
