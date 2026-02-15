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

# 2. CSS STYLING
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
    
    /* ICON CONTAINER (Die Kreise) */
    .icon-container { position: relative; width: 80px; height: 50px; margin: 0 auto 5px; }
    .icon-1 { width: 40px; height: 40px; border-radius: 50%; position: absolute; left: 10px; top: 0; background-size: cover; z-index: 2; border: 2px solid #1e222d; }
    .icon-2 { width: 40px; height: 40px; border-radius: 50%; position: absolute; left: 35px; top: 10px; background-size: cover; z-index: 1; border: 2px solid #1e222d; }
    
    /* SIGNAL BOX */
    .signal-box { 
        font-size: 1.1em; font-weight: 800; text-align: center; 
        padding: 8px; border-radius: 4px; margin-top: 5px; margin-bottom: 10px;
        color: #000; text-shadow: 0px 0px 1px rgba(255,255,255,0.5);
    }
    
    /* GOLDENE WARN-BOX */
    .future-warning {
        border: 2px solid #ffd700;
        background-color: #332b00;
        color: #ffd700;
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
    
    /* --- SCROLLBOX FÜR NEWS --- */
    .news-scroll-container {
        max-height: 200px;       /* Maximale Höhe */
        overflow-y: auto;        /* Scrollbar wenn nötig */
        padding-right: 5px;
        margin-top: 5px;
        background-color: #161a25;
        padding: 5px;
        border-radius: 4px;
    }
    
    /* Scrollbar Styling */
    .news-scroll-container::-webkit-scrollbar { width: 6px; }
    .news-scroll-container::-webkit-scrollbar-track { background: #161a25; }
    .news-scroll-container::-webkit-scrollbar-thumb { background-color: #555; border-radius: 10px; }

    /* News Listen Styles */
    .ff-high { border-left: 3px solid #ff4b4b; padding-left: 6px; margin-bottom: 4px; font-size: 0.8em; line-height: 1.3; }
    .ff-med { border-left: 3px solid #ffa500; padding-left: 6px; margin-bottom: 4px; font-size: 0.8em; line-height: 1.3; }
    .ff-low { border-left: 3px solid #4caf50; padding-left: 6px; margin-bottom: 4px; font-size: 0.8em; line-height: 1.3; color: #aaa; }
    
    .pair-name { color: #d1d4dc; font-weight: bold; font-size: 1.1em; text-align: center; margin-top: 5px; }
    a { color: #2962ff !important; text-decoration: none; }
    a:hover { text-decoration: underline; color: #5e8aff !important; }
    
    .last-update { font-size: 0.7em; color: #787b86; text-align: center; margin-top: 30px; }
</style>
""", unsafe_allow_html=True)

# 3. HELPER: ICONS
def get_icon_url(c):
    crypto = {"BTC": "https://cryptologos.cc/logos/bitcoin-btc-logo.png", "ADA": "https://cryptologos.cc/logos/cardano-ada-logo.png", "XAU": "https://cdn-icons-png.flaticon.com/512/272/272530.png"}
    if c.upper() in crypto: return crypto[c.upper()]
    m = {"USD":"us","JPY":"jp","EUR":"eu","GBP":"gb","CHF":"ch","CAD":"ca","AUD":"au","US30":"us"}
    code = m.get(c.upper(), "un")
    return f"https://flagcdn.com/w160/{code}.png"

# 4. HELPER: SYNONYME
def get_keywords_for_currency(symbol):
    symbol = symbol.upper()
    keywords = [symbol]
    
    if symbol == "USD": keywords.extend(["dollar", "greenback", "fed ", "fomc", "powell", "treasury", "us economy"])
    if symbol == "EUR": keywords.extend(["euro", "ecb", "lagarde", "ez ", "german", "bundesbank"])
    if symbol == "GBP": keywords.extend(["pound", "sterling", "boe ", "bailey", "uk economy", "gilt"])
    if symbol == "JPY": keywords.extend(["yen", "boj ", "ueda", "japan"])
    if symbol == "CHF": keywords.extend(["franc", "snb ", "swiss"])
    if symbol == "CAD": keywords.extend(["loonie", "boc ", "canada", "oil"])
    if symbol == "AUD": keywords.extend(["aussie", "rba ", "australia"])
    if symbol == "BTC": keywords.extend(["bitcoin", "crypto", "sec ", "etf"])
    if symbol == "XAU": keywords.extend(["gold", "bullion", "metal"])
    if symbol == "US30": keywords.extend(["dow", "wall street", "stocks", "sp500"])
    
    return keywords

# 5. HELPER: KALENDER EINTAG
def create_ics(event_title, description):
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

# 6. DATEN LADEN
@st.cache_data(ttl=300, show_spinner=False)
def fetch_calendar_data():
    urls = [
        "https://www.investing.com/rss/news_25.rss",
        "https://www.fxstreet.com/rss/news",
        "https://cointelegraph.com/rss"
    ]
    
    events = []
    high_impact_keywords = ["cpi", "nfp", "gdp", "fomc", "rate decision", "interest rate", "inflation", "payroll"]
    future_keywords = ["preview", "outlook", "forecast", "tomorrow", "week ahead", "projection", "expects", "likely to"]
    
    for url in urls:
        try:
            f = feedparser.parse(url)
            for e in f.entries[:50]: # Viele News laden
                title = e.title
                link = e.link
                lower = title.lower()
                
                impact = "low"
                for k in high_impact_keywords:
                    if k in lower: impact = "high"
                
                is_future = False
                for k in future_keywords:
                    if k in lower: is_future = True
                
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

# 7. ANALYSE LOGIK
def analyze_pair(name, events):
    parts = name.replace(' (Gold)', '').split('/')
    base_sym = parts[0]
    quote_sym = parts[1] if len(parts) > 1 else ""
    
    if "XAU" in name: base_sym = "XAU"
    if "US30" in name: base_sym = "US30"
    if "BTC" in name: base_sym = "BTC"
    
    base_keywords = get_keywords_for_currency(base_sym)
    quote_keywords = get_keywords_for_currency(quote_sym) if quote_sym else []
    
    score = 0
    relevant_news = []
    future_warning = None
    
    for e in events:
        is_relevant = False
        for k in base_keywords:
            if k in e["raw"]: is_relevant = True
        for k in quote_keywords:
            if k in e["raw"]: is_relevant = True
        if "market" in e["raw"]: is_relevant = True
        
        if is_relevant:
            if not e["is_future"]:
                score += e["score"]
            
            if e["is_future"]:
                if future_warning is None:
                    future_warning = e
                elif e["impact"] == "high" and future_warning["impact"] != "high":
                    future_warning = e
                
            relevant_news.append(e)
            
    decision = "NEUTRAL"
    color = "#b2b5be" # Grau
    
    if score >= 1:
        decision = "KAUFEN"
        color = "#00ff00" # Grün
    elif score <= -1:
        decision = "VERKAUFEN"
        color = "#ff4b4b" # Rot
        
    return decision, color, relevant_news, future_warning

# 8. IP FINDEN
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    local_ip = s.getsockname()[0]
    s.close()
    network_url = f"http://{local_ip}:8501"
except: network_url = "http://localhost:8501"


# --- 9. LAYOUT ---
st.title("📅 Future Market Scanner")
tomorrow_date = (datetime.datetime.now() + timedelta(days=1)).strftime('%d.%m.%Y')
st.caption(f"Aktive Prognosen & Vorschau für Morgen ({tomorrow_date})")

cached_data = fetch_calendar_data()

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

# Grid Layout
for i in range(0, len(pairs), 4):
    cols = st.columns(4)
    for j, (name, ticker) in enumerate(pairs[i:i+4]):
        decision, color, news, future_alert = analyze_pair(name, cached_data)
        
        # Icons URLs vorbereiten
        parts = name.replace(' (Gold)', '').split('/')
        b_url = get_icon_url(parts[0])
        q_url = get_icon_url(parts[1] if len(parts)>1 else "USD")
        if "XAU" in name: b_url = get_icon_url("XAU")
        if "BTC" in name: b_url = get_icon_url("BTC")
        if "ADA" in name: b_url = get_icon_url("ADA")
        if "US30" in name: b_url = get_icon_url("US30")
        
        with cols[j]:
            # 1. ICONS & NAME (Jetzt wieder da!)
            st.markdown(f"""
                <div class="icon-container">
                    <div class="icon-1" style="background-image: url('{b_url}');"></div>
                    <div class="icon-2" style="background-image: url('{q_url}');"></div>
                </div>
                <div class='pair-name'>{name}</div>
            """, unsafe_allow_html=True)
            
            # 2. SIGNAL
            st.markdown(f"<div class='signal-box' style='background-color: {color};'>{decision}</div>", unsafe_allow_html=True)
            
            # 3. GOLDENE BOX
            if future_alert:
                st.markdown(f"""
                <div class='future-warning'>
                    <div class='warning-header'>⚠️ VORSCHAU/MORGEN:</div>
                    {future_alert['title']}
                </div>
                """, unsafe_allow_html=True)
                
                ics_data = create_ics(f"{name}: {future_alert['title']}", f"Link: {future_alert['link']}")
                st.download_button("📅 Termin speichern", ics_data, f"event_{name}.ics", "text/calendar", key=f"btn_{i}_{j}")

            # 4. NEWS LISTE MIT SCROLLBAR
            with st.expander(f"News ({len(news)})"):
                if news:
                    # Sortierung
                    news.sort(key=lambda x: (x["impact"] == "high", x["is_future"]), reverse=True)
                    
                    # Hier bauen wir den HTML-String für die Scrollbox
                    news_html = "<div class='news-scroll-container'>"
                    for n in news: # KEIN Limit mehr (zeigen alle)
                        icon = "🔮" if n["is_future"] else "🔥" if n["impact"] == "high" else "📄"
                        css = "ff-high" if n["impact"] == "high" else "ff-med"
                        news_html += f"<div class='{css}'>{icon} <a href='{n['link']}'>{n['title']}</a></div>"
                    news_html += "</div>"
                    
                    st.markdown(news_html, unsafe_allow_html=True)
                else:
                    st.caption("Keine News.")

st.divider()

# UNTEN: TRADINGVIEW WIDGET
st.subheader("📊 Offizieller Kalender")
components.html("""
<div class="tradingview-widget-container">
  <div class="tradingview-widget-container__widget"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-events.js" async>
  { "colorTheme": "dark", "isTransparent": false, "width": "100%", "height": "600", "locale": "de_DE", "importanceFilter": "-1,0,1" }
  </script>
</div>
""", height=600)

with st.sidebar:
    st.header("📱 Handy Link")
    st.image(f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={network_url}")
    st.write(f"`{network_url}`")

st.markdown(f"<div class='last-update'>Live Logic | Auto-Refresh 5 Min | Zeit: {datetime.datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)

time.sleep(300) 
st.rerun()
