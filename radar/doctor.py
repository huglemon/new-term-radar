# --- 文件契约 ---
# [INPUT]: 依赖 config 加载结果、aisa/goanyapi/gsc 的凭证、sources.accounts 的账号数、notify.recipients 的收件人解析。
# [OUTPUT]: 提供 report 与凭证、信号、成本、可达性四组检查函数。
# [POS]: radar 的起飞前检查；只读，不写库、不改快照，回答"跑一次调用什么、通不通、多少钱"。
# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""What a run will do, before it does it: which signals are armed, which credentials
work, and what they cost.

  python -m radar doctor              # checks with the network: every credential proven
  python -m radar doctor --offline    # reads the config and the environment only

Read-only: it writes no report, no database and no snapshot.

Two deliberate spends prove a key works rather than merely that it is set, which is the
failure a blind first run would otherwise bill you for: one AIsa chat with max_tokens=1
(a fraction of a cent) and, when that key is present, one GoAnyAPI related-queries lookup
(6 credits, $0.006, and 20 to 55 seconds).

The dollar figures are data only. Model tokens have no unit price and are left out, as
the modules that spend them do.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

from . import UA, aisa, goanyapi, gsc, notify, review, sources
from .i18n import t

# Unit prices in micro-USD, the October 2026 ones the spending modules document.
MICROS = {
    "x_account": 3000,       # one X advanced search, per account per run (README)
    "site_query": 130000,    # one new-site WHOIS query (README)
    "trends": 1200,          # one Trends lookup (review.MAX_VARIANTS, usecases.py)
    "uc_posts": 3000,        # the post search for one name (usecases.py)
    "uc_volume": 90000,      # one Google Ads volume batch (usecases.py)
    "goany": 6000,           # 6 credits at $0.001 (goanyapi.py)
}
SOURCES_PER_DAY = 3          # the workflow runs ① every 8 hours
GITHUB_LIMIT = "https://api.github.com/rate_limit"


def env(*names: str) -> str:
    """The first of `names` that holds a non-empty value. The value itself never leaves here."""
    for n in names:
        v = (os.environ.get(n) or "").strip()
        if v:
            return v
    return ""


def _row(name: str, state: str, detail: str = "") -> dict:
    return {"name": name, "state": state, "detail": detail}


def aisa_key(cfg: dict, live: bool) -> dict:
    """The one key every paid call goes through. Verified with a one-token chat, which also
    proves the configured judge model exists."""
    model = cfg["judge"]["model"] or "gpt-4.1-mini"
    if not env("AISA_API_KEY"):
        return _row("AISA_API_KEY", "missing", t("doc_aisa_missing"))
    if not live:
        return _row("AISA_API_KEY", "set", t("doc_aisa_untested"))
    try:
        aisa.chat(model, "Answer with one word.", "ping", max_tokens=1)
    except aisa.AisaError as exc:
        return _row("AISA_API_KEY", "failed", str(exc)[:140])
    return _row("AISA_API_KEY", "ok", t("doc_aisa_ok", model=model))


def github_key(live: bool) -> dict:
    """Free, and the one credential whose absence is quiet: 60 requests an hour instead of
    5,000, which caps ② breakout and the README read in ⑥."""
    tok = env("GITHUB_TOKEN", "GH_TOKEN")
    if not live:
        return _row("GITHUB_TOKEN", "set" if tok else "missing", "" if tok else t("doc_gh_missing"))
    req = urllib.request.Request(GITHUB_LIMIT, headers={"User-Agent": UA, "Accept": "application/vnd.github+json"})
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            core = (json.load(res).get("resources") or {}).get("core") or {}
    except (OSError, ValueError) as exc:
        return _row("GITHUB_TOKEN", "failed", f"{type(exc).__name__}: {exc}"[:140])
    return _row("GITHUB_TOKEN", "ok" if tok else "missing",
                t("doc_gh_ok", left=core.get("remaining", "?"), limit=core.get("limit", "?")))


def goany_key(live: bool) -> dict:
    """Optional, and the flakiest dependency: one lookup proves the key and that the service
    answers today."""
    if not goanyapi.key():
        return _row("GOANYAPI_API_KEY", "off", t("doc_goany_off"))
    if not live:
        return _row("GOANYAPI_API_KEY", "set", t("doc_goany_untested"))
    try:
        _, cost = goanyapi.related_queries("gpts")
    except goanyapi.GoAnyError as exc:
        return _row("GOANYAPI_API_KEY", "failed", str(exc)[:140])
    return _row("GOANYAPI_API_KEY", "ok", t("doc_goany_ok", cost=f"{cost / 1e6:.3f}"))


def gsc_key(cfg: dict, live: bool) -> dict:
    """The credential people forget they configured. A refresh proves the token file still
    works; the query itself is free and is not run here."""
    c = cfg.get("gsc") or {}
    if not c.get("site"):
        return _row("gsc", "off", t("doc_gsc_off"))
    name = c.get("token_file", "gsc_token.json")
    if not (cfg["_dir"] / name).exists() and not env("GSC_TOKEN_JSON"):
        return _row("gsc", "missing", t("doc_gsc_missing", file=name))
    if not live:
        return _row("gsc", "set", c["site"])
    try:
        gsc._token(cfg)   # the refresh the signal itself does; it is the part that expires
    except Exception as exc:  # noqa: BLE001 — urllib, json and a malformed file all land here
        return _row("gsc", "failed", f"{type(exc).__name__}: {exc}"[:140])
    return _row("gsc", "ok", t("doc_gsc_ok", site=c["site"]))


def mail_key() -> dict:
    """The three that must be set together: RADAR_EMAIL_TO alone is read with .get and skips
    quietly, but EMAIL_FROM and RESEND_API_KEY are read with [] and raise KeyError."""
    to = env("RADAR_EMAIL_TO")
    if not to:
        return _row("mail", "off", t("doc_mail_off"))
    absent = [k for k in ("EMAIL_FROM", "RESEND_API_KEY") if not env(k)]
    if absent:
        return _row("mail", "failed", t("doc_mail_half", missing=", ".join(absent)))
    try:
        n = len(notify.recipients(to))
    except Exception:  # noqa: BLE001 — recipients only splits, but a doctor never crashes
        n = 1
    return _row("mail", "ok", t("doc_mail_ok", n=n))


def usecase_calls(cfg: dict, with_goany: bool) -> tuple[int, int]:
    """(paid calls, micros) for one ⑥ run: a post search per name, one volume batch, two
    Trends lookups per row, and with GoAnyAPI a related-queries lookup per name plus one
    country series per big row."""
    c = cfg["usecases"]
    n, rows, country = c["per_day"], c["per_day"] + c["trends_max"], c["country_max"]
    calls = n + 1 + 2 * rows
    micros = n * MICROS["uc_posts"] + MICROS["uc_volume"] + 2 * rows * MICROS["trends"]
    if with_goany and c.get("related", True):
        calls += n
        micros += n * MICROS["goany"]
    if with_goany and c.get("country_trends", True):
        calls += country
        micros += country * MICROS["goany"]
    return calls, micros


def signals(cfg: dict, weekly: bool, paid: bool) -> list[dict]:
    """One row per signal for today's `daily`. A signal that is armed while the key it needs
    is missing reads "blocked": that is the failure a first run would bill you for."""

    def row(key: str, label: str, on: bool, calls: int, micros: int, note: str, needs_key: bool = False) -> dict:
        state = "off" if not on else "blocked" if (needs_key and not paid) else "on"
        billed = state == "on"
        return {"key": key, "label": label, "state": state, "calls": calls if billed else 0,
                "micros": micros if billed else 0, "note": note}

    accounts = len(sources.accounts(cfg))
    sites = len(cfg["sitemaps"])
    queries = len(cfg["new_sites"]["queries"])
    rev = cfg["review"]["per_day"] * review.MAX_VARIANTS
    uc_calls, uc_micros = usecase_calls(cfg, bool(goanyapi.key()))
    usd = lambda k: f"{MICROS[k] / 1e6:.4f}".rstrip("0")   # noqa: E731 — one price table, one place
    return [
        row("x", t("doc_sig_x"), accounts > 0, accounts, accounts * MICROS["x_account"], t("doc_note_x", usd=usd("x_account")), True),
        row("hf", t("doc_sig_hf"), True, 0, 0, t("doc_note_free")),
        row("breakout", t("doc_sig_breakout"), True, 0, 0, t("doc_note_github")),
        row("sitemaps", t("doc_sig_sitemaps"), sites > 0, 0, 0, t("doc_note_sites", n=sites)),
        row("newsites", t("doc_sig_newsites"), queries > 0, queries if weekly else 0,
            queries * MICROS["site_query"] if weekly else 0,
            t("doc_note_weekly" if weekly else "doc_note_weekly_off", usd=usd("site_query")), True),
        row("gsc", t("doc_sig_gsc"), bool((cfg.get("gsc") or {}).get("site")), 0, 0, t("doc_note_free")),
        row("usecases", t("doc_sig_uc"), cfg["usecases"]["per_day"] > 0, uc_calls, uc_micros,
            t("doc_note_uc", name=usd("uc_posts"), batch=usd("uc_volume"), trends=usd("trends")), True),
        row("review", t("doc_sig_review"), True, rev, rev * MICROS["trends"], t("doc_note_review", n=rev, usd=usd("trends")), True),
        row("judge", t("doc_sig_judge"), True, 1, 0, t("doc_note_judge"), True),
    ]


def monthly(rows: list[dict], cfg: dict) -> int:
    """One month at the workflow's pace: ① three times a day, the daily signals once, the
    weekly ones about four times. A row reading "blocked" or "off" spends nothing, so it
    counts as nothing: the weekly term is added only when that row is armed."""
    x = next((r["micros"] for r in rows if r["key"] == "x"), 0)
    daily = 30 * (SOURCES_PER_DAY * x + sum(r["micros"] for r in rows if r["key"] != "x"))
    armed = next((r for r in rows if r["key"] == "newsites"), {}).get("state") == "on"
    weekly = round(30 / 7) * len(cfg["new_sites"]["queries"]) * MICROS["site_query"] if armed else 0
    return daily + weekly


def reach(cfg: dict, live: bool) -> dict:
    """One HEAD per sitemap index. A typo'd URL is the failure that costs a whole signal, and
    one request per host is not a crawl."""
    if not cfg["sitemaps"] or not live:
        return {"total": len(cfg["sitemaps"]), "ok": 0, "bad": [], "tested": False}
    ok, bad = 0, []
    for site, s in cfg["sitemaps"].items():
        try:
            req = urllib.request.Request(s["index"], method="HEAD", headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20) as res:
                ok += 1 if res.status < 400 else 0
        except urllib.error.HTTPError as exc:
            if exc.code == 405:      # the host refuses HEAD but the URL is there
                ok += 1
            else:
                bad.append(f"{site}: HTTP {exc.code}")
        except (OSError, KeyError, ValueError) as exc:
            bad.append(f"{site}: {type(exc).__name__}")
    return {"total": len(cfg["sitemaps"]), "ok": ok, "bad": bad, "tested": True}


def state_lines(state: Path) -> list[str]:
    """Whether the radar has history. Read-only: nothing here creates the directory."""
    snaps = len(list(state.glob("*.gz"))) if state.exists() else 0
    db = state / "radar.db"
    if not db.exists():
        return [t("doc_state_new", dir=state)]
    return [t("doc_state_old", dir=state, kb=round(db.stat().st_size / 1024), snaps=snaps)]


def report(cfg: dict, state: Path, live: bool = True, weekly: bool | None = None,
           today: date | None = None) -> str:
    today = today or date.today()
    if weekly is None:
        weekly = today.weekday() == cfg["new_sites"]["weekday"]
    key = aisa_key(cfg, live)
    creds = [key, github_key(live), goany_key(live), gsc_key(cfg, live), mail_key()]
    rows = signals(cfg, weekly, bool(env("AISA_API_KEY")))
    calls = sum(r["calls"] for r in rows)
    micros = sum(r["micros"] for r in rows)

    out = [t("doc_title"), "", t("doc_creds_h"), "", t("doc_creds_cols"), "|---|---|---|"]
    out += [f"| `{c['name']}` | {t('doc_' + c['state'])} | {c['detail'] or t('dash')} |" for c in creds]
    out += ["", t("doc_signals_h"), "", t("doc_signals_cols"), "|---|---|---|---|"]
    out += [f"| {r['label']} | {t('doc_' + r['state'])} | {r['calls']} | {r['note']} |" for r in rows]
    out += ["", t("doc_cost_h"), "",
            t("doc_cost_run", calls=calls, usd=f"{micros / 1e6:.3f}"),
            t("doc_cost_month", usd=f"{monthly(rows, cfg) / 1e6:.2f}")]
    if any(r["state"] == "blocked" for r in rows):
        out.append(t("doc_cost_blocked"))
    out.append(t("doc_cost_tokens"))
    out += ["", t("doc_state_h"), "", *state_lines(state)]
    r = reach(cfg, live)
    if r["tested"]:
        out.append(t("doc_reach_ok", ok=r["ok"], total=r["total"]) if not r["bad"]
                   else t("doc_reach_bad", bad="; ".join(r["bad"])))
    out += ["", t("doc_verdict_ready") if key["state"] != "missing" else t("doc_verdict_fix")]
    return "\n".join(out) + "\n"
