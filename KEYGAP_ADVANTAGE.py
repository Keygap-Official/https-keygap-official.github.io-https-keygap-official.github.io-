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
    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Keygap Report Live</title>
  <style>
    :root {{
      --bg:#08111e; --panel:#101b31; --panel2:#13213b; --line:rgba(255,255,255,.08);
      --text:#eef4ff; --muted:#9db0cf; --accent:#6ee7ff; --shadow:0 18px 50px rgba(0,0,0,.28);
    }}
    * {{ box-sizing:border-box; }}
    body {{
      margin:0;
      font-family:Inter,Arial,sans-serif;
      background:linear-gradient(180deg,#08111e,#0b1526 100%);
      color:var(--text);
      padding:24px;
    }}
    .wrap {{ max-width:980px; margin:0 auto; }}
    .hero, .card {{
      background:linear-gradient(180deg,var(--panel),var(--panel2));
      border:1px solid var(--line);
      border-radius:24px;
      box-shadow:var(--shadow);
    }}
    .hero {{ padding:26px; margin-bottom:18px; }}
    .card {{ padding:22px; margin-top:18px; }}
    .eyebrow {{
      color:var(--muted);
      font-size:12px;
      font-weight:800;
      letter-spacing:.08em;
      text-transform:uppercase;
      margin-bottom:10px;
    }}
    h1 {{
      margin:0 0 10px;
      font-size:clamp(30px,5vw,48px);
      line-height:1;
      letter-spacing:-.04em;
    }}
    h2 {{
      margin:0 0 12px;
      font-size:24px;
      letter-spacing:-.02em;
    }}
    .muted {{ color:var(--muted); }}
    .lead {{
      font-size:18px;
      line-height:1.55;
      color:#d9e6ff;
    }}
    .grid {{
      display:grid;
      grid-template-columns:repeat(2,1fr);
      gap:14px;
      margin-top:18px;
    }}
    .mini {{
      background:rgba(255,255,255,.03);
      border:1px solid var(--line);
      border-radius:18px;
      padding:16px;
    }}
    .mini .label {{
      color:var(--muted);
      font-size:12px;
      font-weight:800;
      letter-spacing:.08em;
      text-transform:uppercase;
      margin-bottom:6px;
    }}
    .mini .value {{
      font-size:22px;
      font-weight:800;
    }}
    ul {{
      margin:0;
      padding-left:18px;
      color:#d9e6ff;
      line-height:1.7;
    }}
    p {{
      margin:0;
      color:#d9e6ff;
      line-height:1.7;
    }}
    .cta {{
      margin-top:18px;
      display:inline-flex;
      align-items:center;
      justify-content:center;
      min-height:48px;
      padding:0 18px;
      border-radius:14px;
      background:linear-gradient(135deg,var(--accent),#9cf3ff);
      color:#07111f;
      font-weight:800;
      text-decoration:none;
    }}
    @media (max-width:700px) {{
      body {{ padding:14px; }}
      .grid {{ grid-template-columns:1fr; }}
      .hero, .card {{ padding:18px; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <div class="eyebrow">Keygap / Report Live</div>
      <h1>BTC Live {fmt_eur(report["price_eur"])}</h1>
      <p class="lead">
        Report operativo aggiornato al {report["updated_at"]}. Questa pagina raccoglie il quadro sintetico di mercato,
        i livelli tecnici principali e una lettura rapida utile sia da smartphone che da desktop.
      </p>

      <div class="grid">
        <div class="mini">
          <div class="label">Bias</div>
          <div class="value">{report["bias"]}</div>
        </div>
        <div class="mini">
          <div class="label">Variazione 24h</div>
          <div class="value">{report["change_24h_pct"]}%</div>
        </div>
        <div class="mini">
          <div class="label">Supporto</div>
          <div class="value">{fmt_eur(report["support_eur"])}</div>
        </div>
        <div class="mini">
          <div class="label">Resistenza</div>
          <div class="value">{fmt_eur(report["resistance_eur"])}</div>
        </div>
      </div>
    </section>

    <section class="card">
      <div class="eyebrow">Scenario operativo</div>
      <h2>Lettura rapida</h2>
      <p>{report["quick_read"]}</p>
    </section>

    <section class="card">
      <div class="eyebrow">Livelli tecnici</div>
      <h2>Range e struttura</h2>
      <ul>
        <li><strong>Massimo 24h:</strong> {fmt_eur(report["high_24h_eur"])}</li>
        <li><strong>Minimo 24h:</strong> {fmt_eur(report["low_24h_eur"])}</li>
        <li><strong>Supporto chiave:</strong> {fmt_eur(report["support_eur"])}</li>
        <li><strong>Resistenza chiave:</strong> {fmt_eur(report["resistance_eur"])}</li>
        <li><strong>Volatilità:</strong> {report["volatility"]}</li>
      </ul>
    </section>

    <section class="card">
      <div class="eyebrow">Interpretazione</div>
      <h2>Che cosa significa adesso</h2>
      <p>
        BTC quota {fmt_eur(report["price_eur"])} e si muove con una variazione giornaliera del
        {report["change_24h_pct"]}%. Il quadro di breve periodo resta <strong>{report["bias"]}</strong>.
        In questo contesto, il livello di {fmt_eur(report["support_eur"])} rappresenta l’area da difendere,
        mentre {fmt_eur(report["resistance_eur"])} è il primo livello da superare per migliorare il tono operativo.
      </p>
    </section>

    <section class="card">
      <div class="eyebrow">Conclusione</div>
      <h2>Takeaway finale</h2>
      <p>
        Questo dossier serve come sintesi operativa: rapido da leggere, ma abbastanza completo da dare un contesto utile.
        La home premium mostra il segnale; questa pagina conserva la lettura più strutturata del momento.
      </p>
      <a class="cta" href="{SITE_URL}">Apri dashboard live</a>
    </section>
  </div>
</body>
</html>"""
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
    lines = "\n".join([f"• {n['title']}" for n in top_news]) if top_news else "• Nessuna news disponibile"

    text = (
        "⚡ KEYGAP MARKET UPDATE\n\n"
        f"BTC/EUR: {fmt_eur(report['price_eur'])}\n"
        f"Bias operativo: {report['bias']}\n"
        f"Supporto chiave: {fmt_eur(report['support_eur'])}\n"
        f"Resistenza chiave: {fmt_eur(report['resistance_eur'])}\n"
        f"Variazione 24h: {report['change_24h_pct']}%\n\n"
        f"Top news del momento:\n{lines}\n\n"
        f"Scenario rapido:\n{report['quick_read']}\n\n"
        f"Apri dashboard:\n{SITE_URL}"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    r = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=25)
    r.raise_for_status()
    print("✅ Telegram inviato")

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
