#!/usr/bin/env python3
import json
import os
import pickle
import random
import subprocess
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

SITE_URL = "https://keygap-official.github.io/"
BLOG_ID = "2744764892823107807"
SCOPES = ["https://www.googleapis.com/auth/blogger"]

# --- TELEGRAM IN CHIARO (SICURO) ---
TELEGRAM_BOT_TOKEN = "8736329123:AAFa9k_rtKOGQmpwXGICRu-jjdAGEUuWTZM"
TELEGRAM_CHAT_ID = "@KeygapTerminal"

# --- ADSTERRA MONETIZZAZIONE ---
AD_POPUNDER = """
<script src="https://pl28819682.profitablecpmratenetwork.com/07/47/37/074737f2d1be0f3c0e9de0585a695fd7.js"></script>
"""

GOOGLE_NEWS_RSS = (
    "https://news.google.com/rss/search?"
    "q=bitcoin+OR+crypto+when:1d&hl=it&gl=IT&ceid=IT:it"
)


def fmt_eur(v):
    return f"€ {v:,.0f}".replace(",", ".")


def now_it():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def filename_stamp():
    return datetime.now().strftime("%d_%m_%Y_%H_%M")


def fetch_btc():
    r = requests.get(
        "https://api.coingecko.com/api/v3/coins/markets",
        params={
            "vs_currency": "eur",
            "ids": "bitcoin",
            "price_change_percentage": "24h",
        },
        timeout=20,
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

    bias = (
        "moderatamente rialzista"
        if change > 1
        else "moderatamente ribassista"
        if change < -1
        else "neutrale"
    )
    volatility = "alta" if abs(change) > 3 else "media" if abs(change) > 1 else "contenuta"
    quick_read = (
        f"Prezzo in equilibrio nel breve. {fmt_eur(support)} resta il supporto da difendere, "
        f"mentre {fmt_eur(resistance)} è la prima resistenza utile per un'accelerazione."
    )

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
    USED_NEWS.write_text(
        json.dumps(sorted(list(used))[-500:], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


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

    for n in items[:6]:
        used.add(n["sig"])

    save_used_news(used)

    for n in items:
        n.pop("sig", None)

    return {"updated_at": now_it(), "items": items}


def write_latest_report_html(report):
    """Genera un report esteticamente identico alla tua nuova dashboard, iniettando Adsterra"""
    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Keygap Report Live #{report["id"]}</title>
  {AD_POPUNDER}
  <style>
    :root {{
      --bg:#060b14;
      --panel:#0e1728;
      --panel2:#132038;
      --line:rgba(255,255,255,.08);
      --text:#edf4ff;
      --muted:#98abc7;
      --accent:#6ee7ff;
      --shadow:0 18px 50px rgba(0,0,0,.35);
    }}
    * {{ box-sizing:border-box; }}
    body {{
      margin:0;
      font-family:Inter,system-ui,-apple-system,sans-serif;
      background:linear-gradient(180deg,var(--bg),#0a1322 100%);
      color:var(--text);
      padding:22px;
    }}
    .wrap {{ max-width:980px; margin:0 auto; }}
    .hero, .card {{
      background:linear-gradient(180deg,var(--panel),var(--panel2));
      border:1px solid var(--line);
      border-radius:24px;
      box-shadow:var(--shadow);
    }}
    .hero {{ padding:30px; margin-bottom:22px; position:relative; overflow:hidden; }}
    .hero::after {{
      content:""; position:absolute; right:-50px; top:-50px; width:200px; height:200px;
      border-radius:50%; background:radial-gradient(circle, rgba(110,231,255,.15), transparent 70%); pointer-events:none;
    }}
    .card {{ padding:24px; margin-top:22px; }}
    .eyebrow {{
      display:inline-flex; align-items:center; gap:8px; padding:6px 12px; border-radius:999px;
      background:rgba(110,231,255,.10); border:1px solid rgba(110,231,255,.20);
      color:#bff6ff; font-size:12px; font-weight:800; letter-spacing:.08em; text-transform:uppercase;
      margin-bottom:14px;
    }}
    h1 {{ margin:0 0 10px; font-size:clamp(32px,5vw,54px); line-height:1; letter-spacing:-.04em; }}
    h2 {{ margin:0 0 14px; font-size:24px; letter-spacing:-.02em; }}
    .lead {{ font-size:18px; line-height:1.55; color:#d7e3f8; }}
    .grid {{ display:grid; grid-template-columns:repeat(2,1fr); gap:14px; margin-top:22px; }}
    .mini {{
      background:rgba(255,255,255,.03); border:1px solid var(--line); border-radius:18px; padding:18px;
    }}
    .mini .label {{
      color:var(--muted); font-size:12px; font-weight:800; letter-spacing:.08em; text-transform:uppercase; margin-bottom:8px;
    }}
    .mini .value {{ font-size:24px; font-weight:800; }}
    ul {{ margin:0; padding-left:20px; color:#d7e3f8; line-height:1.8; }}
    p {{ margin:0; color:#d7e3f8; line-height:1.7; }}
    .cta {{
      margin-top:22px; display:inline-flex; align-items:center; justify-content:center;
      min-height:50px; padding:0 24px; border-radius:14px;
      background:linear-gradient(135deg,var(--accent),#9cf3ff); color:#07111f; font-weight:800; text-decoration:none;
    }}
    @media (max-width:700px) {{
      body {{ padding:14px; }}
      .grid {{ grid-template-columns:1fr; }}
      .hero, .card {{ padding:20px; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <div class="eyebrow">Keygap / Report Live #{report["id"]}</div>
      <h1>BTC Live {fmt_eur(report["price_eur"])}</h1>
      <p class="lead">
        Report operativo aggiornato al {report["updated_at"]}. Sintesi di mercato e livelli tecnici per operatività rapida.
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

    <section class="card" style="text-align:center;">
      <h2 style="margin-bottom:10px;">Terminale Live</h2>
      <p style="margin-bottom:10px;">Per i grafici interattivi completi e le notizie aggiornate in tempo reale, accedi alla dashboard.</p>
      <a class="cta" href="{SITE_URL}">Apri Dashboard Elite</a>
    </section>
  </div>
</body>
</html>"""
    
    LATEST_REPORT_HTML.write_text(html, encoding="utf-8")
    report_file = REPORTS_DIR / f"Report_Mondiale_{filename_stamp()}.html"
    report_file.write_text(html, encoding="utf-8")
    return report_file.name


def rebuild_archivio():
    """Genera la pagina archivio usando una formattazione multi-linea blindata per evitare SyntaxError"""
    files = sorted(REPORTS_DIR.glob("*.html"), reverse=True)
    items = "\n".join([f'<li style="margin-bottom:10px;"><a href="Report_Finanziari/{f.name}" style="color:#6ee7ff;text-decoration:none;">{f.name}</a></li>' for f in files[:300]])
    
    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Archivio report</title>
</head>
<body style="font-family:Inter,Arial,sans-serif;background:#060b14;color:#eef4ff;padding:24px;">
    <div style="max-width:800px;margin:0 auto;">
        <h1 style="border-bottom:1px solid rgba(255,255,255,0.1);padding-bottom:10px;">Archivio report</h1>
        <ul style="list-style:none;padding:0;">
            {items}
        </ul>
    </div>
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


def publish_blogger(report, news):
    service = get_blogger_service()
    if not service:
        print("ℹ️ Blogger non configurato: skip publish.")
        return

    top = news.get("items", [])[:3]
    news_html = "".join([f"<li>{n['title']}</li>" for n in top])

    content = (
        "<div style='font-family:Arial,sans-serif;line-height:1.6;max-width:850px;margin:auto;"
        "background:#0e1728;color:#edf4ff;padding:28px;border-radius:18px'>"
        f"<h1 style='color:#6ee7ff'>Keygap AdVantage Elite</h1>"
        f"<p><strong>Aggiornato:</strong> {report['updated_at']}</p>"
        f"<p><strong>BTC/EUR:</strong> {fmt_eur(report['price_eur'])}</p>"
        f"<p><strong>Bias:</strong> {report['bias']}</p>"
        f"<p><strong>Supporto:</strong> {fmt_eur(report['support_eur'])} · "
        f"<strong>Resistenza:</strong> {fmt_eur(report['resistance_eur'])}</p>"
        f"<p>{report['quick_read']}</p>"
        f"<h3>Top news</h3><ul>{news_html}</ul>"
        f"<p><a href='{SITE_URL}' style='color:#00ff88;font-weight:bold;'>Apri dashboard live</a></p>"
        "</div>"
    )

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

    # Dinamicità per non rendere i post noiosi
    emojis = ["⚡", "🚀", "🔥", "⚠️", "📊", "🎯", "👁️"]
    alert_icon = random.choice(emojis)

    # Frasi contestuali in base al mercato
    if "rialzista" in report['bias']:
        mood = "📈 I tori stanno spingendo. Il mercato prova a forzare la resistenza."
        tiktok_hook = f"Bitcoin in spinta verso l'alto a {fmt_eur(report['price_eur'])}! Riuscirà a rompere la resistenza?"
    elif "ribassista" in report['bias']:
        mood = "📉 Pressione in vendita. Fondamentale tenere i supporti per evitare crolli."
        tiktok_hook = f"Attenzione al ribasso! Bitcoin scende a {fmt_eur(report['price_eur'])}. Ecco il supporto da difendere."
    else:
        mood = "⚖️ Fase di consolidamento. Volumi in attesa del prossimo strappo direzionale."
        tiktok_hook = f"Calma piatta per Bitcoin a {fmt_eur(report['price_eur'])}. Preparatevi al prossimo grande movimento."

    # Post Telegram + TikTok/Social in fondo
    text = (
        f"{alert_icon} KEYGAP ADVANTAGE | MARKET UPDATE\n\n"
        f"💰 BTC/EUR Spot: {fmt_eur(report['price_eur'])}\n"
        f"📊 Variazione 24h: {report['change_24h_pct']}%\n\n"
        f"🎯 LIVELLI OPERATIVI:\n"
        f"🛡️ Supporto: {fmt_eur(report['support_eur'])}\n"
        f"⚔️ Resistenza: {fmt_eur(report['resistance_eur'])}\n"
        f"Compass: {report['bias'].upper()}\n\n"
        f"{mood}\n\n"
        f"📰 TOP NEWS:\n"
        f"{lines}\n\n"
        f"🌐 Dashboard e Report Live:\n{SITE_URL}\n\n"
        f"➖➖➖➖➖➖➖➖\n"
        f"📱 FORMAT TIKTOK / SHORTS:\n"
        f"{tiktok_hook} Entra nel terminale per il dossier live.\n"
        f"#KeygapAdVantage #Bitcoin #CryptoITA #Trading #Mercati"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(
            url,
            data={"chat_id": TELEGRAM_CHAT_ID, "text": text},
            timeout=25,
        )
        r.raise_for_status()
        print("✅ Telegram inviato")
    except Exception as e:
        print(f"❌ Errore Telegram: {e}")


def is_git_repo():
    return (ROOT / ".git").exists()


def git_publish(report_id):
    if not is_git_repo():
        print("ℹ️ Cartella non inizializzata come repo git: skip publish.")
        return

    # LO SCUDO ANTI-PAGINA BIANCA
    with open(ROOT / ".nojekyll", "w") as f:
        f.write("")

    cmds = [
        ["git", "add", "."],
        ["git", "commit", "-m", f"Elite update {report_id}"],
        ["git", "push", "origin", "main"],
    ]

    for cmd in cmds:
        res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)

        if cmd[1] == "commit" and res.returncode != 0 and "nothing to commit" in (res.stdout + res.stderr).lower():
            print("ℹ️ Nessuna modifica da committare")
            continue

        if res.returncode != 0:
            print(res.stdout)
            print(res.stderr)
            raise RuntimeError(f"Errore comando: {' '.join(cmd)}")

        if res.stdout.strip():
            print(res.stdout.strip())
        if res.stderr.strip():
            print(res.stderr.strip())

    print(f"✅ Update {report_id} pubblicato")


def run_cycle():
    REPORTS_DIR.mkdir(exist_ok=True)

    # 1. Genera dati JSON (da cui la tua Dashboard premium prenderà i dati in automatico)
    report = fetch_btc()
    news = fetch_news()

    # 2. Genera HTML del Report (Ultra moderno con Adsterra)
    report_file = write_latest_report_html(report)
    report["latest_report_file"] = f"Report_Finanziari/{report_file}"

    # 3. Salva i JSON 
    LATEST_REPORT_JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    LATEST_NEWS.write_text(
        json.dumps(news, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    rebuild_archivio()
    send_telegram(report, news)
    publish_blogger(report, news)
    git_publish(report["id"])


if __name__ == "__main__":
    import time
    while True:
        try:
            run_cycle()
        except Exception as e:
            print(f"Errore nel ciclo: {e}")
        
        print("Attendo 30 minuti per il prossimo ciclo...")
        time.sleep(1800)