import os, subprocess, datetime

# --- CONFIGURAZIONE ---
REPO_PATH = os.path.expanduser("~") + "/Desktop/Keygap_AdVantage"
ARTICOLI_PATH = os.path.join(REPO_PATH, "articoli_pronti")

def ottieni_contenuto():
    ora = datetime.datetime.now().hour
    file_target = "mattina.txt" if 5 <= ora < 15 else "sera.txt"
    path_file = os.path.join(ARTICOLI_PATH, file_target)
    
    if os.path.exists(path_file):
        with open(path_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "ATTENDERE: Caricamento dati di mercato in corso..."

testo_notizia = ottieni_contenuto()
ora_esatta = datetime.datetime.now().strftime("%H:%M")

# --- LAYOUT "BREAKING NEWS" TOTALE ---
HTML_MASTER = f'''
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>KEYGAP TERMINAL</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{ background: #000; color: #fff; font-family: sans-serif; margin: 0; }}
        /* FASCIA NOTIZIA GIGANTE */
        .top-banner {{ 
            background: #ff0000; /* ROSSO ACCESO */
            color: white; 
            padding: 20px; 
            text-align: center; 
            font-size: 30px; 
            font-weight: bold;
            border-bottom: 5px solid #fff;
            animation: pulse 2s infinite;
        }}
        @keyframes pulse {{
            0% {{ background-color: #ff0000; }}
            50% {{ background-color: #8b0000; }}
            100% {{ background-color: #ff0000; }}
        }}
        .content-grid {{ display: grid; grid-template-columns: 1fr; gap: 10px; padding: 10px; }}
    </style>
</head>
<body>
    <div class="top-banner">
        ⚠️ ULTIMATUM {ora_esatta}: {testo_notizia}
    </div>

    <div class="content-grid">
        <div style="height: 600px;">
            <iframe src="https://s.tradingview.com/widgetembed/?symbol=SPX&theme=dark" width="100%" height="100%" frameborder="0"></iframe>
        </div>
    </div>
</body>
</html>
'''

try:
    os.chdir(REPO_PATH)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(HTML_MASTER)
    
    # Invia il comando a GitHub
    subprocess.run(["git", "add", "."])
    subprocess.run(["git", "commit", "-m", "Notizia Urgente in Home"])
    subprocess.run(["git", "push", "origin", "master"])
    print("✅ SITO AGGIORNATO! La notizia ora è in rosso gigante in cima alla pagina.")
except Exception as e:
    print(f"❌ Errore: {e}")