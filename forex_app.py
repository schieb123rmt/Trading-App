import streamlit as st
import feedparser
from textblob import TextBlob
import datetime
from datetime import timedelta
import time
import socket
import streamlit.components.v1 as components

# 1. Konfiguration
st.set_page_config(page_title="Trading ATM Ultimate", layout="wide")

# 2. CSS STYLING (Goldene Box + TradingView Dark Mode)
st.markdown("""
<style>
    /* Globaler Dark Mode */
    .stApp { background-color: #0e1117; }
    
    /* Container Style */
    div[data-testid="column"] {
        background-color: #1e222d;
        border-radius: 8px;
        padding: 10px;
        border: 1px solid #2a2e39;
        margin-bottom: 10px;
    }
    
    /* SIGNAL BOX (Kaufen/Verkaufen) */
    .signal-box { 
        font-size: 1.1em; font-weight: 800; text-align: center; 
        padding: 8px; border-radius: 4px; margin-top: 5px; margin-bottom: 10px;
        color: #000; text-shadow: 0px 0px 1px rgba(255,255,255,0.5);
    }
    
    /* --- DIE GOLDENE WARN-BOX (Dein Wunsch-Design) --- */
    .future-warning {
        border: 2px solid #ffd700;       /* Goldener Rand */
        background-color: #332b00;       /* Dunkler Hintergrund */
        color: #ffd700;                  /* Goldene Schrift */
        padding: 10px; 
        border-radius: 6px; 
        font-size: 0.85em; 
        margin-top: 5px; 
        margin-bottom: 5px;
        text-align: center; 
        font-weight: bold;
        line-height: 1.4;
        box-shadow: 0 0 10px rgba(255, 215, 0, 0.1);
    }
    
    .warning-header {
        text-transform: uppercase;
        font-size: 0.9em;
        margin-bottom: 5px;
        text-decoration: underline;
    }
    
    /* News Listen Styles (Forex Factory Farben) */
    .ff-high { border-left: 4px solid #ff4b4b; padding-left: 8px; margin-bottom: 6px; font-size: 0.85em; }
    .ff-med { border-left: 4px solid #ffa500; padding-left: 8px; margin-bottom: 6px; font-size: 0.85em; }
    .ff-low { border-left: 4px solid #4caf50; padding-left: 8px; margin-bottom: 6px; font-size: 0.85em; color: #aaa; }
    
    .pair-name { color: #d1d4dc; font-weight: bold; font-size: 1em; text-align: center; }
    a { color: #2962ff !important; text-decoration: none; }
    a:hover { text-decoration: underline; color: #5e8aff !important; }
    
    .last-update { font-size: 0.7em; color: #787b86; text-align: center; margin-top: 30px; }
</style>
""", unsafe_allow_html=True)

# 3. HELPER: ERWEITERTE SUCHE (Synonyme)
def get_keywords_for_currency(symbol):
    symbol = symbol.upper()
    keywords = [symbol]
    
    # Damit finden wir News, auch wenn das Währungskürzel nicht explizit genannt wird
    if symbol == "USD": keywords.extend(["dollar", "greenback", "fed ", "fomc", "powell", "treasury", "us economy"])
    if symbol == "EUR": keywords.extend(["euro", "ecb", "lagarde", "ez ", "german", "bundesbank"])
    if symbol == "GBP": keywords.extend(["pound", "sterling", "boe ", "bailey", "uk economy", "gilt"])
    if symbol == "JPY": keywords.extend(["yen", "boj ", "ueda", "japan"])
    if symbol == "CHF": keywords.extend(["franc", "snb ", "swiss"])
    if symbol == "CAD": keywords.extend(["loonie", "boc ", "canada", "oil"]) # Öl wichtig für CAD
    if symbol == "AUD": keywords.extend(["aussie", "rba ", "australia"])
    if symbol == "BTC": keywords.extend(["bitcoin", "crypto", "sec ", "etf"])
    if symbol == "XAU": keywords.extend(["gold", "bullion", "metal"])
    if symbol == "US30": keywords.extend(["dow", "wall street", "stocks", "sp500"])
    
    return keywords

# 4. HELPER: KALENDER EINTAG GENERIEREN
def create_ics(event_title, description):
    # Setzt Termin auf Morgen 09:00
    tomorrow = datetime.datetime.now() + timedelta(days=1)
    start_time = tomorrow.replace(hour=9, minute=0, second=0).strftime('%Y%m%dT%H%M%S')
    end_time = tomorrow.replace(hour=10, minute=0, second=0).strftime('%Y%m%dT%H%M%S')
    
    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Trading ATM//Future Scanner//EN
BEGIN:VEVENT
UID:{int(time.time())}@tradingatm.app
DTSTAMP:{datetime.datetime.now().strftime('%Y%m%dT%H%M%S')}
DTSTART:{start_time}
DTEND:{end_time}
SUMMARY:⚡ Markt-Vorschau: {event_title}
DESCRIPTION:{description}
BEGIN:VALARM
TRIGGER:-PT15M
ACTION:DISPLAY
DESCRIPTION:Reminder
END:VALARM
END:VEVENT
END:VCALENDAR"""
    return ics_content

# 5. DATEN LADEN (RSS FEEDS)
@st.cache_data(ttl=300, show_spinner=False)
def fetch_calendar_data():
    urls = [
        "https://www.investing.com/rss/news_25.rss", # Wirtschaftskalender
        "https://www.fxstreet.com/rss/news",         # Forex News
        "https://cointelegraph.com/rss"              # Krypto
    ]
    
    events = []
    
    # Trigger-Wörter
    high_impact_keywords = ["cpi", "nfp", "gdp", "fomc", "rate decision", "interest rate", "inflation", "payroll"]
    future_keywords = ["preview", "outlook", "forecast", "tomorrow", "week ahead", "projection", "expects", "likely to"]
    
    for url in urls:
        try:
            f = feedparser.parse(url)
            # Wir scannen 50 Artikel pro Feed für maximale Abdeckung
            for e in f.entries[:50]:
                title = e.title
                link = e.link
                lower = title.lower()
                
                # Impact Check
                impact = "low"
                for k in high_impact_keywords:
                    if k in lower: impact = "high"
                
                # Future Check (Ist es für morgen?)
                is_future = False
                for k in future_keywords:
                    if k in lower: is_future = True
                
                # Signal Check (Bullish/Bearish)
                signal_score = 0
                if "beat" in lower or "above" in lower or "stronger" in lower or "hike" in lower or "bullish" in lower:
                    signal_score = 1
                elif "miss" in lower or "below" in lower or "weaker" in lower or "cut" in lower or "bearish" in lower:
                    signal_score = -1
                
                events.append({
                    "title": title,
                    "link": link,
                    "impact": impact,
                    "score": signal_score,
                    "is_future": is_future,
                    "raw": lower
                })
        except: continue
    return events

# 6. ANALYSE LOGIK PRO PAAR
def analyze_pair(name, events):
    # Währungspaare aufsplitten
    parts = name.replace(' (Gold)', '').split('/')
    base_sym = parts[0]
    quote_sym = parts[1] if len(parts) > 1 else ""
    
    # Spezialfälle
    if "XAU" in name: base_sym = "XAU"
    if "US30" in name: base_sym = "US30"
    if "BTC" in name: base_sym = "BTC"
    
    # Synonyme laden
    base_keywords = get_keywords_for_currency(base_sym)
    quote_keywords = get_keywords_for_currency(quote_sym) if quote_sym else []
    
    score = 0
    relevant_news = []
    future_warning = None
    
    for e in events:
        is_relevant = False
        
        # Prüfung: Enthält die News eines der Keywords?
        for k in base_keywords:
            if k in e["raw"]: is_relevant = True
        for k in quote_keywords:
            if k in e["raw"]: is_relevant = True
        if "market" in e["raw"]: is_relevant = True
        
        if is_relevant:
            # Score berechnen (nur aktuelle News zählen in das Signal)
            if not e["is_future"]:
                score += e["score"]
            
            # Die "Goldene Box" Logik: Wir suchen die wichtigste Zukunfts-News
            if e["is_future"]:
                if future_warning is None:
                    future_warning = e
                # Wenn wir schon eine haben, überschreiben wir sie nur, wenn die neue "High Impact" ist
                elif e["impact"] == "high" and future_warning["impact"] != "high":
                    future_warning = e
                
            relevant_news.append(e)
            
    # Signal Text & Farbe
    decision = "NEUTRAL"
    color = "#b2b5be" # Grau
    
    if score >= 1:
        decision = "KAUFEN"
        color = "#00ff00" # Grün
    elif score <= -1:
        decision = "VERKAUFEN"
        color = "#ff4b4b" # Rot
        
    return decision, color, relevant_news, future_warning

# 7. IP FÜR QR CODE FINDEN
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    local_ip = s.getsockname()[0]
    s.close()
    network_url = f"http://{local_ip}:8501"
except: network_url = "http://localhost:8501"


# --- 8. LAYOUT AUFBAU ---
st.title("📅 Future Market Scanner")
# Dynamisches Datum für Morgen anzeigen
tomorrow_date = (datetime.datetime.now() + timedelta(days=1)).strftime('%d.%m.%Y')
st.caption(f"Aktive Prognosen & Vorschau für Morgen ({tomorrow_date})")

cached_data = fetch_calendar_data()

# LISTE ALLER 14 PAARE
pairs = [
    ("USD/JPY", "USDJPY=X"),
    ("CHF/JPY", "CHFJPY=X"),
    ("EUR/JPY", "EURJPY=X"),
    ("EUR/GBP", "EURGBP=X"),
    ("GBP/JPY", "GBPJPY=X"),
    ("USD/CAD", "USDCAD=X"),
    ("US30", "^DJI"),
    ("XAU/USD", "GC=F"),
    ("EUR/USD", "EURUSD=X"),
    ("GBP/CAD", "GBPCAD=X"),
    ("EUR/CHF", "EURCHF=X"),
    ("USD/CHF", "USDCHF=X"),
    ("BTC/USD", "BTC-USD"),
    ("ADA/USDT", "ADA-USD")
]

# Grid Layout (4 Spalten)
for i in range(0, len(pairs), 4):
    cols = st.columns(4)
    for j, (name, ticker) in enumerate(pairs[i:i+4]):
        decision, color, news, future_alert = analyze_pair(name, cached_data)
        
        with cols[j]:
            # 1. Name
            st.markdown(f"<div class='pair-name'>{name}</div>", unsafe_allow_html=True)
            
            # 2. Signal Box (Kaufen/Verkaufen)
            st.markdown(f"<div class='signal-box' style='background-color: {color};'>{decision}</div>", unsafe_allow_html=True)
            
            # 3. DIE GOLDENE VORSCHAU BOX (Nur wenn Vorschau da ist)
            if future_alert:
                st.markdown(f"""
                <div class='future-warning'>
                    <div class='warning-header'>⚠️ VORSCHAU/MORGEN:</div>
                    {future_alert['title']}
                </div>
                """, unsafe_allow_html=True)
                
                # 4. Kalender Button (In der goldenen Box Logik)
                ics_data = create_ics(f"{name}: {future_alert['title']}", f"Link: {future_alert['link']}")
                st.download_button(
                    label="📅 Termin speichern",
                    data=ics_data,
                    file_name=f"event_{name}.ics",
                    mime="text/calendar",
                    key=f"btn_{i}_{j}",
                    help="Erstellt einen Kalendereintrag für Morgen 09:00 Uhr"
                )

            # 5. News Expander
            with st.expander(f"News ({len(news)})"):
                if news:
                    # Sortierung: Erst High Impact, dann Future
                    news.sort(key=lambda x: (x["impact"] == "high", x["is_future"]), reverse=True)
                    for n in news[:5]:
                        # Kleine Icons für die Liste
                        icon = "🔮" if n["is_future"] else "🔥" if n["impact"] == "high" else "📄"
                        css = "ff-high" if n["impact"] == "high" else "ff-med"
                        st.markdown(f"<div class='{css}'>{icon} <a href='{n['link']}'>{n['title']}</a></div>", unsafe_allow_html=True)
                else:
                    st.caption("Keine Daten.")

st.divider()

# UNTEN: TRADINGVIEW WIDGET
st.subheader("📊 Offizieller Kalender (Kontrolle)")
components.html("""
<div class="tradingview-widget-container">
  <div class="tradingview-widget-container__widget"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-events.js" async>
  { "colorTheme": "dark", "isTransparent": false, "width": "100%", "height": "600", "locale": "de_DE", "importanceFilter": "-1,0,1" }
  </script>
</div>
""", height=600)

# SIDEBAR: HANDY ZUGANG
with st.sidebar:
    st.header("📱 Handy Link")
    st.image(f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={network_url}")
    st.write(f"`{network_url}`")
    st.info("Scanner für heute & morgen.")

st.markdown(f"<div class='last-update'>Live Logic | Auto-Refresh 5 Min | Zeit: {datetime.datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)

time.sleep(300) 
st.rerun()
