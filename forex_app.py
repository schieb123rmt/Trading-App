import streamlit as st
import feedparser
from textblob import TextBlob
import datetime
from datetime import timedelta
import time
import socket
import streamlit.components.v1 as components

# 1. Konfiguration (Muss ganz oben stehen)
st.set_page_config(page_title="Trading ATM Future", layout="wide")

# CSS: Styling
st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    div[data-testid="column"] {
        background-color: #1e222d;
        border-radius: 8px;
        padding: 10px;
        border: 1px solid #2a2e39;
        margin-bottom: 10px;
    }
    .signal-box { 
        font-size: 1.1em; font-weight: 800; text-align: center; 
        padding: 8px; border-radius: 4px; margin-top: 5px;
        color: #000; text-shadow: 0px 0px 1px rgba(255,255,255,0.5);
    }
    .future-warning {
        border: 1px solid #ffd700; background-color: #332b00; color: #ffd700;
        padding: 8px; border-radius: 4px; font-size: 0.85em; margin-top: 8px; text-align: center; line-height: 1.4;
    }
    .ff-high { border-left: 4px solid #ff4b4b; padding-left: 8px; margin-bottom: 6px; font-size: 0.85em; }
    .ff-med { border-left: 4px solid #ffa500; padding-left: 8px; margin-bottom: 6px; font-size: 0.85em; }
    .ff-low { border-left: 4px solid #4caf50; padding-left: 8px; margin-bottom: 6px; font-size: 0.85em; color: #aaa; }
    
    .pair-name { color: #d1d4dc; font-weight: bold; font-size: 1em; text-align: center; }
    a { color: #2962ff !important; text-decoration: none; }
    a:hover { text-decoration: underline; color: #5e8aff !important; }
    .last-update { font-size: 0.7em; color: #787b86; text-align: center; margin-top: 30px; }
</style>
""", unsafe_allow_html=True)

# --- HELPER: SYNONYME FINDEN (Das Gehirn für mehr Treffer) ---
def get_keywords_for_currency(symbol):
    symbol = symbol.upper()
    keywords = [symbol] # Standard: USD
    
    # Erweiterte Begriffsliste für mehr News-Treffer
    if symbol == "USD": keywords.extend(["dollar", "greenback", "fed ", "fomc", "powell", "treasury", "us economy"])
    if symbol == "EUR": keywords.extend(["euro", "ecb", "lagarde", "ez ", "german", "bundesbank"])
    if symbol == "GBP": keywords.extend(["pound", "sterling", "boe ", "bailey", "uk economy", "gilt"])
    if symbol == "JPY": keywords.extend(["yen", "boj ", "ueda", "japan"])
    if symbol == "CHF": keywords.extend(["franc", "snb ", "swiss"])
    if symbol == "CAD": keywords.extend(["loonie", "boc ", "canada", "oil"]) # Öl ist wichtig für CAD
    if symbol == "AUD": keywords.extend(["aussie", "rba ", "australia"])
    if symbol == "NZD": keywords.extend(["kiwi", "rbnz", "zealand"])
    if symbol == "BTC": keywords.extend(["bitcoin", "crypto", "sec "])
    if symbol == "XAU": keywords.extend(["gold", "bullion", "metal"])
    if symbol == "US30": keywords.extend(["dow", "wall street", "stocks", "sp500"])
    
    return keywords

# --- HELPER: KALENDER DATEI ---
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
SUMMARY:⚡ Markt-Check: {event_title}
DESCRIPTION:{description}
BEGIN:VALARM
TRIGGER:-PT15M
ACTION:DISPLAY
DESCRIPTION:Reminder
END:VALARM
END:VEVENT
END:VCALENDAR"""
    return ics_content

# --- 1. DATEN HOLEN ---
@st.cache_data(ttl=300, show_spinner=False)
def fetch_calendar_data():
    urls = [
        "https://www.investing.com/rss/news_25.rss", 
        "https://www.fxstreet.com/rss/news",
        "https://cointelegraph.com/rss"
    ]
    
    events = []
    # Trigger-Wörter
    high_impact_keywords = ["cpi", "nfp", "gdp", "fomc", "rate decision", "interest rate", "inflation", "payroll"]
    future_keywords = ["preview", "outlook", "forecast", "tomorrow", "week ahead", "due", "expects", "projection", "likely"]
    
    for url in urls:
        try:
            f = feedparser.parse(url)
            # WICHTIG: Limit erhöht auf 50, um mehr News zu fangen
            for e in f.entries[:50]:
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
                signal_text = "News"
                
                if "beat" in lower or "above" in lower or "stronger" in lower or "hike" in lower or "bullish" in lower or "jump" in lower:
                    signal_score = 1
                    signal_text = "Bullish"
                elif "miss" in lower or "below" in lower or "weaker" in lower or "cut" in lower or "bearish" in lower or "drop" in lower:
                    signal_score = -1
                    signal_text = "Bearish"
                
                events.append({
                    "title": title,
                    "link": link,
                    "impact": impact,
                    "score": signal_score,
                    "signal_text": signal_text,
                    "is_future": is_future,
                    "raw": lower
                })
        except: continue
    return events

# --- 2. ANALYSE PRO PAAR (Jetzt mit Synonym-Suche) ---
def analyze_pair(name, events):
    parts = name.replace(' (Gold)', '').split('/')
    base_sym = parts[0]
    quote_sym = parts[1] if len(parts) > 1 else ""
    
    if "XAU" in name: base_sym = "XAU"
    if "US30" in name: base_sym = "US30"
    if "BTC" in name: base_sym = "BTC"
    
    # Hole Synonyme (z.B. CAD -> Loonie, Oil, Canada)
    base_keywords = get_keywords_for_currency(base_sym)
    quote_keywords = get_keywords_for_currency(quote_sym) if quote_sym else []
    
    score = 0
    relevant_news = []
    future_warning = None
    
    for e in events:
        is_relevant = False
        
        # Prüfe Base Währung (z.B. EUR)
        for k in base_keywords:
            if k in e["raw"]: is_relevant = True
            
        # Prüfe Quote Währung (z.B. USD)
        for k in quote_keywords:
            if k in e["raw"]: is_relevant = True
            
        if "market" in e["raw"]: is_relevant = True # Globale News
        
        if is_relevant:
            if not e["is_future"]:
                score += e["score"]
            
            # Priorisiere Future Warnings
            if e["is_future"] and (e["impact"] == "high" or "outlook" in e["raw"]):
                future_warning = e
                
            relevant_news.append(e)
            
    decision = "NEUTRAL"
    color = "#b2b5be"
    
    if score >= 1:
        decision = "KAUFEN"
        color = "#00ff00"
    elif score <= -1:
        decision = "VERKAUFEN"
        color = "#ff4b4b"
        
    return decision, color, relevant_news, future_warning

# --- 3. IP ---
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    local_ip = s.getsockname()[0]
    s.close()
    network_url = f"http://{local_ip}:8501"
except: network_url = "http://localhost:8501"


# --- 4. LAYOUT ---
st.title("📅 Future Market Scanner")
st.caption(f"Scannt nach Signalen für Heute & Morgen ({datetime.datetime.now().strftime('%d.%m.%Y')})")

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
        
        with cols[j]:
            st.markdown(f"<div class='pair-name'>{name}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='signal-box' style='background-color: {color};'>{decision}</div>", unsafe_allow_html=True)
            
            # 1. ZUKUNFTS-WARNUNG (Ganz oben, Gelb)
            if future_alert:
                st.markdown(f"""
                <div class='future-warning'>
                    ⚠️ <b>Vorschau/Morgen:</b><br>
                    {future_alert['title']}
                </div>
                """, unsafe_allow_html=True)
                
                ics_data = create_ics(f"{name}: {future_alert['title']}", f"Link: {future_alert['link']}")
                st.download_button(
                    label="📅 Termin speichern",
                    data=ics_data,
                    file_name=f"event_{name}.ics",
                    mime="text/calendar",
                    key=f"btn_{i}_{j}",
                    help="Speichert diesen Event in deinen Outlook/Google Kalender"
                )

            # 2. LISTE ALLER WICHTIGEN NEWS (Darunter)
            # Wir zeigen jetzt bis zu 5 relevante News an, nicht nur 3
            with st.expander(f"Relevante News ({len(news)})", expanded=True): # expanded=True öffnet es direkt
                if news:
                    # Sortieren: Erst High Impact, dann Future, dann Rest
                    news.sort(key=lambda x: (x["impact"] == "high", x["is_future"]), reverse=True)
                    
                    for n in news[:5]: # Zeige Top 5
                        tag = ""
                        if n["is_future"]: tag = "🔮 "
                        elif n["impact"] == "high": tag = "🔥 "
                        
                        css = "ff-med"
                        if n["impact"] == "high": css = "ff-high"
                        elif n["score"] == 0 and not n["is_future"]: css = "ff-low"
                        
                        st.markdown(f"<div class='{css}'>{tag}<a href='{n['link']}'>{n['title']}</a></div>", unsafe_allow_html=True)
                else:
                    st.caption("Keine spezifischen News.")

st.divider()
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
    st.header("📱 App Link")
    st.image(f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={network_url}")
    st.write(f"`{network_url}`")

time.sleep(180) 
st.rerun()
