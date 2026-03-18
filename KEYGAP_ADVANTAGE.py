#!/usr/bin/env python3
import json, os, random, subprocess, pickle
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET
import requests

ROOT = Path(__file__).resolve().parent
REPORTS_DIR = ROOT / "Report_Finanziari"
LATEST_NEWS = ROOT / "latest_news.json"
LATEST_REPORT_JSON = ROOT / "latest_report.json"
LATEST_REPORT_HTML = ROOT / "latest_report.html"
ARCHIVIO = ROOT / "archivio.html"
USED_NEWS = ROOT / "used_news.json"
SITE_URL = "https://giampierodeluca676-lgtm.github.io/"
BLOG_ID = "2744764892823107807"
SCOPES = ['https://www.googleapis.com/auth/blogger']

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q=bitcoin+OR+crypto+when:1d&hl=it&gl=IT&ceid=IT:it"

def fmt_eur(v):
    return f"€ {v:,.0f}".replace(",", ".")

def now_it():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

def filename_stamp():
    return datetime.now().strftime("%d_%m_%Y_%H_%M")

def fetch_btc():
    r = requests.get(
        "https://api.coingecko.com/api/v3/coins/markets",
        params={"vs_currency":"eur","ids":"bitcoin","price_change_percentage":"24h"},
        timeout=20
    )
    r.raise_for_status()
    data = r.json()[0]
    price = float(data.get("current_price") or 0)
    high = float(data.get("high_24h") or price)
    low = float(data.get("low_24h") or price)
    change = float(data.get("price_change_percentage_24h") or 0)
    span = max(high - low, max(price * 0.002, 1))
    support = round(max(low, price - span * 0.25), 2)
    resistance = round(max(price + span * 0.25, high if high > price else price * 1.0025), 2)
    if support >= resistance:
        support = round(price * 0.9975, 2)
        resistance = round(price * 1.0025, 2)
    bias = "moderatamente rialzista" if change > 1 else "moderatamente ribassista" if change < -1 else "neutrale"
    volatility = "alta" if abs(change) > 3 else "media" if abs(change) > 1 else "contenuta"
    quick_read = f"Prezzo in equilibrio nel breve. {fmt_eur(support)} resta il supporto da difendere, mentre {fmt_eur(resistance)} è la prima resistenza utile per un'accelerazione."
    return {
        "id": random.randint(10000, 99999),
        "updated_at": now_it(),
        "price_eur": round(price, 2),
        "change_24h_pct": round(change, 2),
        "high_24h_eur": round(high, 2),
        "low_24h_eur": round(low, 2),
        "support_eur": round(support, 2),
        "resistance_eur": round(resistance, 2),
        "bias": bias,
        "volatility": volatility,
        "quick_read": quick_read,
    }

def load_used_news():
    if USED_NEWS.exists():
        try:
            return set(json.loads(USED_NEWS.read_text(encoding="utf-8")))
        except Exception:
            return set()
    return set()

def save_used_news(used):
    USED_NEWS.write_text(json.dumps(sorted(list(used))[-500:], ensure_ascii=False, indent=2), encoding="utf-8")

def fetch_news():
    r = requests.get(GOOGLE_NEWS_RSS, timeout=20)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    used = load_used_news()
    items = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        if " - " in title:
            title_part, source = title.rsplit(" - ", 1)
        else:
            title_part, source = title, "News"
        sig = f"{title_part}|{source}"
        items.append({
            "title": title_part,
            "link": link,
            "source": source,
            "published_at": pub,
            "is_new": sig not in used,
            "sig": sig
        })
        if len(items) >= 12:
            break
    for n in items[:6]:
        used.add(n["sig"])
    save_used_news(used)
    for n in items:
        n.pop("sig", None)
    return {"updated_at": now_it(), "items": items}

def write_latest_report_html(report):
    html = f'''<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Keygap Report Live</title>
<style>body{{margin:0;font-family:Inter,Arial,sans-serif;background:#08111e;color:#eef4ff;padding:24px}}.wrap{{max-width:900px;margin:0 auto}}.card{{background:#101b31;border:1px solid rgba(255,255,255,.08);border-radius:22px;padding:22px;box-shadow:0 18px 50px rgba(0,0,0,.28)}}h1{{margin:0 0 14px;font-size:32px}}.muted{{color:#9db0cf}}.grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;margin-top:18px}}.mini{{background:#13213b;border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:16px}}@media(max-width:700px){{.grid{{grid-template-columns:1fr}}}}</style></head>
<body><div class="wrap"><div class="card"><div class="muted">Keygap / Ultimo report</div><h1>BTC live {fmt_eur(report["price_eur"])}</h1><p class="muted">Aggiornato: {report["updated_at"]}</p><div class="grid"><div class="mini"><strong>Bias</strong><br>{report["bias"]}</div><div class="mini"><strong>Variazione 24h</strong><br>{report["change_24h_pct"]}%</div><div class="mini"><strong>Supporto</strong><br>{fmt_eur(report["support_eur"])}</div><div class="mini"><strong>Resistenza</strong><br>{fmt_eur(report["resistance_eur"])}</div></div><p style="margin-top:18px">{report["quick_read"]}</p><p><a href="{SITE_URL}" style="color:#6ee7ff">Apri dashboard live</a></p></div></div></body></html>'''
    LATEST_REPORT_HTML.write_text(html, encoding="utf-8")
    report_file = REPORTS_DIR / f"Report_Mondiale_{filename_stamp()}.html"
    report_file.write_text(html, encoding="utf-8")
    return report_file.name

def rebuild_archivio():
    files = sorted(REPORTS_DIR.glob("*.html"), reverse=True)
    items = "\\n".join([f'<li><a href="Report_Finanziari/{f.name}">{f.name}</a></li>' for f in files[:300]])
    html = f'<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Archivio report</title></head><body style="font-family:Inter,Arial,sans-serif;background:#08111e;color:#eef4ff;padding:24px"><h1>Archivio report</h1><ul>{items}</ul></body></html>'
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

def publish_blogger(report, news):
    service = get_blogger_service()
    if not service:
        print("ℹ️ Blogger non configurato: skip publish.")
        return
    top = news.get("items", [])[:3]
    news_html = "".join([f"<li>{n['title']}</li>" for n in top])
    content = f"<div style='font-family:Arial,sans-serif;line-height:1.6;max-width:850px;margin:auto;background:#101b31;color:#eef4ff;padding:28px;border-radius:18px'><h1 style='color:#6ee7ff'>Keygap AdVantage Elite</h1><p><strong>Aggiornato:</strong> {report['updated_at']}</p><p><strong>BTC/EUR:</strong> {fmt_eur(report['price_eur'])}</p><p><strong>Bias:</strong> {report['bias']}</p><p><strong>Supporto:</strong> {fmt_eur(report['support_eur'])} · <strong>Resistenza:</strong> {fmt_eur(report['resistance_eur'])}</p><p>{report['quick_read']}</p><h3>Top news</h3><ul>{news_html}</ul><p><a href='{SITE_URL}' style='color:#6ee7ff'>Apri dashboard live</a></p></div>"
    title = f"Keygap Elite BTC Update #{report['id']} - {report['updated_at']}"
    body = {"kind": "blogger#post", "title": title, "content": content}
    try:
        service.posts().insert(blogId=BLOG_ID, body=body).execute()
        print("✅ Blogger pubblicato")
    except Exception as e:
        print(f"⚠️ Blogger errore: {e}")

def send_telegram(report, news):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("ℹ️ Telegram non configurato: skip invio.")
        return
    top_news = news.get("items", [])[:3]
    lines = "\\n".join([f"• {n['title']}" for n in top_news]) if top_news else "• Nessuna news disponibile"
    text = f"⚡ KEYGAP ELITE UPDATE\\n\\nBTC/EUR: {fmt_eur(report['price_eur'])}\\nBias: {report['bias']}\\nSupporto: {fmt_eur(report['support_eur'])}\\nResistenza: {fmt_eur(report['resistance_eur'])}\\n\\nTop news:\\n{lines}\\n\\nLettura rapida:\\n{report['quick_read']}\\n\\n🌐 Dashboard live:\\n{SITE_URL}"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    r = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=20)
    r.raise_for_status()
    print("✅ Telegram inviato")

def git_publish(report_id):
    cmds = [["git","add","."],["git","commit","-m",f"Elite update {report_id}"],["git","push","origin","main"]]
    for cmd in cmds:
        res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if cmd[1] == "commit" and res.returncode != 0 and "nothing to commit" in (res.stdout + res.stderr).lower():
            print("ℹ️ Nessuna modifica da committare")
            continue
        if res.returncode != 0:
            print(res.stdout); print(res.stderr)
            raise SystemExit(f"Errore comando: {' '.join(cmd)}")
        if res.stdout.strip(): print(res.stdout.strip())
        if res.stderr.strip(): print(res.stderr.strip())
    print(f"✅ Update {report_id} pubblicato")

def run_cycle():
    REPORTS_DIR.mkdir(exist_ok=True)
    report = fetch_btc()
    news = fetch_news()
    report_file = write_latest_report_html(report)
    report["latest_report_file"] = f"Report_Finanziari/{report_file}"
    LATEST_REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    LATEST_NEWS.write_text(json.dumps(news, ensure_ascii=False, indent=2), encoding="utf-8")
    rebuild_archivio()
    send_telegram(report, news)
    publish_blogger(report, news)
    git_publish(report["id"])

if __name__ == "__main__":
    run_cycle()
