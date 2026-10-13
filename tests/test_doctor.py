# --- 文件契约 ---
# [INPUT]: 依赖 pytest 夹具与 radar.doctor、radar.config。
# [OUTPUT]: 提供起飞前检查的离线测试：缺少凭证时的阻挡、成本模型与不泄密。
# [POS]: tests 的 doctor 验证入口；只跑离线路径，联网检查靠 test_radar 的替身约定排除。
# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""doctor, offline: what it blocks, what it counts, and what it never prints."""
from datetime import date

import pytest

from radar import doctor


def rows_by_key(cfg, **kw):
    return {r["key"]: r for r in doctor.signals(cfg, kw.get("weekly", False), kw.get("paid", True))}


# --- what a missing key blocks ------------------------------------------------------

def test_without_the_key_the_paid_signals_read_blocked_and_spend_nothing(cfg):
    cfg["x_accounts"] = {"labs": ["OpenAI"], "bloggers": []}
    rows = rows_by_key(cfg, paid=False)
    assert rows["x"]["state"] == "blocked" and rows["usecases"]["state"] == "blocked"
    assert rows["review"]["state"] == "blocked" and rows["judge"]["state"] == "blocked"
    assert all(rows[k]["calls"] == 0 and rows[k]["micros"] == 0
               for k in ("x", "usecases", "review", "judge"))


def test_the_free_signals_still_run_without_a_key(cfg):
    cfg["sitemaps"] = {"glama": {"index": "https://glama.ai/sitemap.xml"}}
    rows = rows_by_key(cfg, paid=False)
    assert rows["hf"]["state"] == "on" and rows["breakout"]["state"] == "on"
    assert rows["sitemaps"]["state"] == "on"


def test_a_signal_with_nothing_configured_reads_off_not_blocked(cfg):
    rows = rows_by_key(cfg)   # the default config follows no X account
    assert rows["x"]["state"] == "off"


# --- the cost model -----------------------------------------------------------------

def test_the_keyword_table_costs_what_the_module_documents(cfg):
    """usecases.py documents $0.003 a name, $0.09 the batch and $0.0012 a lookup; five names
    and ten rows give $0.141, or $0.219 with GoAnyAPI, which the README rounds to $0.15 and
    $0.22. Pin both, so a price or a default that drifts shows up here."""
    cfg["usecases"]["per_day"] = 5
    assert doctor.usecase_calls(cfg, False) == (36, 141_000)
    assert doctor.usecase_calls(cfg, True) == (49, 219_000)


def test_one_daily_run_adds_up_from_the_signals(cfg):
    cfg["x_accounts"] = {"labs": ["a", "b", "c"], "bloggers": []}
    rows = list(rows_by_key(cfg).values())
    assert sum(r["calls"] for r in rows) == 3 + 36 + 15 + 1   # X, keyword table, review, judge
    assert sum(r["micros"] for r in rows) == 3 * 3000 + 141_000 + 15 * 1200


def test_a_month_counts_the_weekly_signal_four_times(cfg):
    cfg["x_accounts"] = {"labs": ["a"], "bloggers": []}
    rows = list(rows_by_key(cfg).values())
    assert doctor.monthly(rows, cfg) == 30 * (3 * 3000 + 141_000 + 18_000) + 4 * 130_000


def test_a_month_without_a_key_costs_nothing(cfg):
    cfg["x_accounts"] = {"labs": ["a"]}
    rows = list(rows_by_key(cfg, paid=False).values())
    assert doctor.monthly(rows, cfg) == 0


# --- credentials --------------------------------------------------------------------

def test_the_aisa_row_names_the_configs_own_model_when_it_answers(cfg, monkeypatch):
    """The ping uses the configured judge model, so a model that does not exist fails here
    rather than in the first billed run."""
    monkeypatch.setenv("AISA_API_KEY", "k")
    monkeypatch.setattr(doctor.aisa, "chat", lambda *a, **k: "ok")
    cfg["judge"]["model"] = "gpt-4.1-mini"
    assert "gpt-4.1-mini" in doctor.aisa_key(cfg, live=True)["detail"]
    assert doctor.aisa_key(cfg, live=False)["state"] == "set"


def test_the_aisa_row_carries_the_api_error_when_the_key_is_rejected(cfg, monkeypatch):
    monkeypatch.setenv("AISA_API_KEY", "k")

    def refused(*a, **k):
        raise doctor.aisa.AisaError("HTTP 401: invalid key")
    monkeypatch.setattr(doctor.aisa, "chat", refused)
    row = doctor.aisa_key(cfg, live=True)
    assert row["state"] == "failed" and "401" in row["detail"]


def test_mail_reports_the_three_that_must_travel_together(cfg, monkeypatch):
    monkeypatch.setenv("RADAR_EMAIL_TO", "me@example.com")
    monkeypatch.delenv("EMAIL_FROM", raising=False)
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    row = doctor.mail_key()
    assert row["state"] == "failed" and "EMAIL_FROM" in row["detail"] and "RESEND_API_KEY" in row["detail"]


def test_mail_is_off_rather_than_broken_when_nothing_is_set(monkeypatch):
    monkeypatch.delenv("RADAR_EMAIL_TO", raising=False)
    assert doctor.mail_key()["state"] == "off"


def test_mail_counts_the_recipients_once_all_three_are_set(monkeypatch):
    monkeypatch.setenv("RADAR_EMAIL_TO", "a@example.com, b@example.com")
    monkeypatch.setenv("EMAIL_FROM", "radar@example.com")
    monkeypatch.setenv("RESEND_API_KEY", "re_x")
    row = doctor.mail_key()
    assert row["state"] == "ok" and "2" in row["detail"]


def test_goanyapi_is_off_until_its_key_is_set(monkeypatch):
    monkeypatch.delenv("GOANYAPI_API_KEY", raising=False)
    assert doctor.goany_key(live=False)["state"] == "off"
    monkeypatch.setenv("GOANYAPI_API_KEY", "g")
    assert doctor.goany_key(live=False)["state"] == "set"


def test_search_console_is_off_with_an_empty_config(cfg):
    assert doctor.gsc_key(cfg, live=False)["state"] == "off"


def test_search_console_knows_a_site_with_no_token(cfg):
    cfg["gsc"] = {"site": "sc-domain:example.com", "token_file": "gsc_token.json"}
    row = doctor.gsc_key(cfg, live=False)
    assert row["state"] == "missing" and "gsc_token.json" in row["detail"]


# --- what it never does -------------------------------------------------------------

def test_a_secret_is_never_printed(cfg, tmp_path, monkeypatch):
    monkeypatch.setenv("AISA_API_KEY", "sk-super-secret-value")
    monkeypatch.setenv("RESEND_API_KEY", "re-super-secret-value")
    text = doctor.report(cfg, tmp_path, live=False, weekly=False)
    assert "super-secret-value" not in text


def test_offline_never_touches_the_network(cfg, tmp_path, monkeypatch):
    def explode(*a, **k):
        raise AssertionError("offline doctor made a request")
    monkeypatch.setattr(doctor.urllib.request, "urlopen", explode)
    text = doctor.report(cfg, tmp_path, live=False, weekly=False)
    assert "AISA_API_KEY" in text


def test_doctor_says_which_sitemaps_did_not_answer(cfg):
    cfg["sitemaps"] = {"glama": {"index": "https://glama.ai/sitemap.xml"}}
    assert doctor.reach(cfg, live=False)["tested"] is False


# --- state --------------------------------------------------------------------------

def test_a_fresh_state_directory_reads_as_a_first_run(cfg, tmp_path):
    assert "does not exist" in " ".join(doctor.state_lines(tmp_path))


def test_a_state_directory_with_a_database_reads_as_history(tmp_path):
    (tmp_path / "radar.db").write_bytes(b"x" * 2048)
    (tmp_path / "x.json.gz").write_bytes(b"")
    line = " ".join(doctor.state_lines(tmp_path))
    assert "2 KB" in line and "1 snapshot" in line


def test_doctor_creates_no_directory(cfg, tmp_path):
    missing = tmp_path / "never-made"
    doctor.report(cfg, missing, live=False, weekly=False)
    assert not missing.exists()


@pytest.mark.parametrize("weekly,expected", [(True, 1), (False, 0)])
def test_the_weekly_signal_is_billed_only_on_its_day(cfg, weekly, expected):
    row = rows_by_key(cfg, weekly=weekly)["newsites"]
    assert row["state"] == "on" and row["calls"] == expected


def test_the_report_is_the_same_shape_on_any_day(cfg, tmp_path):
    for day in (date(2026, 10, 12), date(2026, 10, 13)):
        text = doctor.report(cfg, tmp_path, live=False, today=day)
        assert text.startswith("## New-term radar · doctor") and text.endswith(".\n")
