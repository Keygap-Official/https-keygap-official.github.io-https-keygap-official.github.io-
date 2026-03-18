#!/usr/bin/env python3
from __future__ import annotations

import json
import logging
import os
import pickle
import random
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import requests

ROOT = Path(__file__).resolve().parent
REPORTS_DIR = ROOT / "Report_Finanziari"
LATEST_NEWS = ROOT / "latest_news.json"
LATEST_REPORT_JSON = ROOT / "latest_report.json"
LATEST_REPORT_HTML = ROOT / "latest_report.html"
ARCHIVIO = ROOT / "archivio.html"
USED_NEWS = ROOT / "used_news.json"
LOG_FILE = ROOT / "keygap_runtime.log"

SITE_URL = "https://giampierodeluca676-lgtm.github.io/"
BLOG_ID = "2744764892823107807"
SCOPES = ["https://www.googleapis.com/auth/blogger"]

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

GOOGLE_NEWS_RSS = (
    "https://news.google.com/rss/search?"
    "q=bitcoin+OR+crypto+when:1d&hl=it&gl=IT&ceid=IT:it"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
log = logging.getLogger("keygap")


@dataclass
class Report:
    report_id: int
    updated_at: str
    price_eur: float
    change_24h_pct: float
    high_24h_eur: float
    low_24h_eur: float
    support_eur: float
    resistance_eur: float
    bias: str
    volatility: str
    quick_read: str
    latest_report_file: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.report_id,
            "updated_at": self.updated_at,
            "price_eur": self.price_eur,
            "change_24h_pct": self.change_24h_pct,
            "high_24h_eur": self.high_24h_eur,
            "low_24h_eur": self.low_24h_eur,
            "support_eur": self.support_eur,
            "resistance_eur": self.resistance_eur,
            "bias": self.bias,
            "volatility": self.volatility,
            "quick_read": self.quick_read,
            "latest_report_file": self.latest_report_file or "latest_report.html",
        }


def ensure_dirs() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def fmt_eur(v: float | int) -> str:
    return f"€ {v:,.0f}".replace(",", ".")


def now_it() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def filename_stamp() -> str:
    return datetime.now().strftime("%d_%m_%Y_%H_%M")


def safe_json_write(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_btc() -> Report:
    r = requests.get(
        "https://api.coingecko.com/api/v3/coins/markets",
        params={"vs_currency": "eur", "ids": "bitcoin", "price_change_percentage": "24h"},
        timeout=25,
    )
    r.raise_for_status()
    data = r.json()[0]

    price = float(data.get("current_price") or 0)
    high = float(data.get("high_24h") or price)
    low = float(data.get("low_24h") or price)
    change = float(data.get("price_change_percentage_24h") or 0)

    span = max(high - low, max(price * 0.003, 1))
    support = round(max(low, price - span * 0.25), 2)
    resistance = round(max(price + span * 0.25, high if high > price else price * 1.0025), 2)

    if support >= resistance:
        support = round(price * 0.9975, 2)
        resistance = round(price * 1.0025, 2)

    if change > 1:
        bias = "moderatamente rialzista"
    elif change < -1:
        bias = "moderatamente ribassista"
    else:
        bias = "neutrale"

    volatility = "alta" if abs(change) > 3 else "media" if abs(change) > 1 else "contenuta"
    quick_read = (
        f"Prezzo in equilibrio nel breve. {fmt_eur(support)} resta il supporto da difendere, "
        f"mentre {fmt_eur(resistance)} è la prima resistenza utile per un'accelerazione."
    )

    return Report(
        report_id=random.randint(10000, 99999),
        updated_at=now_it(),
        price_eur=round(price, 2),
        change_24h_pct=round(change, 2),
        high_24h_eur=round(high, 2),
        low_24h_eur=round(low, 2),
        support_eur=round(support, 2),
        resistance_eur=round(resistance, 2),
        bias=bias,
        volatility=volatility,
        quick_read=quick_read,
    )


def load_used_news() -> set[str]:
    if not USED_NEWS.exists():
        return set()
    try:
        data = json.loads(USED_NEWS.read_text(encoding="utf-8"))
        return set(data if isinstance(data, list) else [])
    except Exception:
        return set()


def save_used_news(used: set[str]) -> None:
    safe_json_write(USED_NEWS, sorted(list(used))[-500:])


def fetch_news() -> dict[str, Any]:
    r = requests.get(GOOGLE_NEWS_RSS, timeout=25)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    used = load_used_news()
    items: list[dict[str, Any]] = []

    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()

        if " - " in title:
            title_part, source = title.rsplit(" - ", 1)
        else:
            title_part, source = title, "News"

        sig = f"{title_part}|{source}"
        items.append(
            {
                "title": title_part,
                "link": link,
                "source": source,
                "published_at": pub,
                "is_new": sig not in used,
                "sig": sig,
            }
        )
        if len(items) >= 12:
            break

    for item in items[:6]:
        used.add(item["sig"])
    save_used_news(used)

    for item in items:
        item.pop("sig", None)

    return {"updated_at": now_it(), "items": items}


def write_latest_report_html(report: Report) -> str:
    html = f"""<!DOCTYPE html>
<html lang=\"it\">
<head>
  <meta charset=\"UTF-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
  <title>Keygap Report Live</title>
  <style>
    body{{margin:0;font-family:Inter,Arial,sans-serif;background:#08111e;color:#eef4ff;padding:24px}}
    .wrap{{max-width:900px;margin:0 auto}}
    .card{{background:#101b31;border:1px solid rgba(255,255,255,.08);border-radius:22px;padding:22px;box-shadow:0 18px 50px rgba(0,0,0,.28)}}
    h1{{margin:0 0 14px;font-size:32px}}
    .muted{{color:#9db0cf}}
    .grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;margin-top:18px}}
    .mini{{background:#13213b;border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:16px}}
    @media(max-width:700px){{.grid{{grid-template-columns:1fr}}}}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <div class=\"card\">
      <div class=\"muted\">Keygap / Ultimo report</div>
      <h1>BTC live {fmt_eur(report.price_eur)}</h1>
      <p class=\"muted\">Aggiornato: {report.updated_at}</p>
      <div class=\"grid\">
        <div class=\"mini\"><strong>Bias</strong><br>{report.bias}</div>
        <div class=\"mini\"><strong>Variazione 24h</strong><br>{report.change_24h_pct}%</div>
        <div class=\"mini\"><strong>Supporto</strong><br>{fmt_eur(report.support_eur)}</div>
        <div class=\"mini\"><strong>Resistenza</strong><br>{fmt_eur(report.resistance_eur)}</div>
      </div>
      <p style=\"margin-top:18px\">{report.quick_read}</p>
      <p><a href=\"{SITE_URL}\" style=\"color:#6ee7ff\">Apri dashboard live</a></p>
    </div>
  </div>
</body>
</html>"""
    LATEST_REPORT_HTML.write_text(html, encoding="utf-8")
    report_file = REPORTS_DIR / f"Report_Mondiale_{filename_stamp()}.html"
    report_file.write_text(html, encoding="utf-8")
    return report_file.name


def rebuild_archivio() -> None:
    files = sorted(REPORTS_DIR.glob("*.html"), reverse=True)
    items = "\n".join([f'<li><a href="Report_Finanziari/{f.name}">{f.name}</a></li>' for f in files[:300]])
    html = f"""<!DOCTYPE html>
<html lang=\"it\">
<head>
  <meta charset=\"UTF-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
  <title>Archivio report</title>
</head>
<body style=\"font-family:Inter,Arial,sans-serif;background:#08111e;color:#eef4ff;padding:24px\">
  <h1>Archivio report</h1>
  <ul>{items}</ul>
</body>
</html>"""
    ARCHIVIO.write_text(html, encoding="utf-8")


def get_blogger_service():
    try:
        from googleapiclient.discovery import build
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
    except Exception:
        return None

    creds = None
    token_pickle = ROOT / "token.pickle"
    client_secrets = ROOT / "client_secrets.json"

    if token_pickle.exists():
        with open(token_pickle, "rb") as token:
            creds = pickle.load(token)

    if not creds or not getattr(creds, "valid", False):
        if creds and getattr(creds, "expired", False) and getattr(creds, "refresh_token", None):
            creds.refresh(Request())
        elif client_secrets.exists():
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets), SCOPES)
            creds = flow.run_local_server(port=0)
        else:
            return None

        with open(token_pickle, "wb") as token:
            pickle.dump(creds, token)

    return build("blogger", "v3", credentials=creds)


def publish_blogger(report: Report, news: dict[str, Any]) -> None:
    service = get_blogger_service()
    if not service:
        log.info("Blogger non configurato: skip publish.")
        return

    top = news.get("items", [])[:3]
    news_html = "".join([f"<li>{n['title']}</li>" for n in top])

    content = (
        "<div style='font-family:Arial,sans-serif;line-height:1.6;max-width:850px;margin:auto;"
        "background:#101b31;color:#eef4ff;padding:28px;border-radius:18px'>"
        f"<h1 style='color:#6ee7ff'>Keygap AdVantage Elite</h1>"
        f"<p><strong>Aggiornato:</strong> {report.updated_at}</p>"
        f"<p><strong>BTC/EUR:</strong> {fmt_eur(report.price_eur)}</p>"
        f"<p><strong>Bias:</strong> {report.bias}</p>"
        f"<p><strong>Supporto:</strong> {fmt_eur(report.support_eur)} · "
        f"<strong>Resistenza:</strong> {fmt_eur(report.resistance_eur)}</p>"
        f"<p>{report.quick_read}</p>"
        f"<h3>Top news</h3><ul>{news_html}</ul>"
        f"<p><a href='{SITE_URL}' style='color:#6ee7ff'>Apri dashboard live</a></p></div>"
    )

    title = f"Keygap Elite BTC Update #{report.report_id} - {report.updated_at}"
    body = {"kind": "blogger#post", "title": title, "content": content}

    try:
        service.posts().insert(blogId=BLOG_ID, body=body).execute()
        log.info("Blogger pubblicato")
    except Exception as e:
        log.warning("Blogger errore: %s", e)


def send_telegram(report: Report, news: dict[str, Any]) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log.info("Telegram non configurato: skip invio.")
        return

    top_news = news.get("items", [])[:3]
    lines = "\n".join([f"• {n['title']}" for n in top_news]) if top_news else "• Nessuna news disponibile"

    text = (
        "⚡ KEYGAP ELITE UPDATE\n\n"
        f"📅 Aggiornato: {report.updated_at}\n"
        f"₿ BTC/EUR: {fmt_eur(report.price_eur)}\n"
        f"📈 Variazione 24h: {report.change_24h_pct}%\n"
        f"🎯 Bias: {report.bias}\n"
        f"🛡 Supporto: {fmt_eur(report.support_eur)}\n"
        f"🚀 Resistenza: {fmt_eur(report.resistance_eur)}\n\n"
        f"📰 Top news:\n{lines}\n\n"
        f"🧠 Lettura rapida:\n{report.quick_read}\n\n"
        f"🌐 Dashboard live:\n{SITE_URL}"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    r = requests.post(
        url,
        data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "disable_web_page_preview": False,
        },
        timeout=25,
    )
    r.raise_for_status()
    log.info("Telegram inviato")


def is_git_repo() -> bool:
    return (ROOT / ".git").exists()


def git_publish(report_id: int) -> None:
    if not is_git_repo():
        log.warning("Cartella non inizializzata come repo git: skip publish.")
        return

    cmds = [
        ["git", "add", "."],
        ["git", "commit", "-m", f"Elite update {report_id}"],
        ["git", "push", "origin", "main"],
    ]

    for cmd in cmds:
        res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)

        if cmd[1] == "commit" and res.returncode != 0 and "nothing to commit" in (res.stdout + res.stderr).lower():
            log.info("Nessuna modifica da committare")
            continue

        if res.returncode != 0:
            log.error(res.stdout)
            log.error(res.stderr)
            raise RuntimeError(f"Errore comando: {' '.join(cmd)}")

        if res.stdout.strip():
            log.info(res.stdout.strip())
        if res.stderr.strip():
            log.info(res.stderr.strip())

    log.info("Update %s pubblicato", report_id)


def run_cycle() -> None:
    ensure_dirs()
    report = fetch_btc()
    news = fetch_news()

    report_file = write_latest_report_html(report)
    report.latest_report_file = f"Report_Finanziari/{report_file}"

    safe_json_write(LATEST_REPORT_JSON, report.to_dict())
    safe_json_write(LATEST_NEWS, news)

    rebuild_archivio()
    send_telegram(report, news)
    publish_blogger(report, news)
    git_publish(report.report_id)


if __name__ == "__main__":
    run_cycle()

