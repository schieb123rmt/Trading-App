import streamlit as st
import feedparser
from textblob import TextBlob
import datetime
import time
import socket
import streamlit.components.v1 as components

# 1. Konfiguration
st.set_page_config(page_title="TV Calendar Ultimate", layout="wide")

# CSS: TradingView Dark Mode & Forex Factory Farben
st.markdown("""
<style>
    /* Hintergrund & Container */
    .stApp { background-color: #0e1117; }
    div[data-testid="column"] {
        background-color: #1e222d;
        border-radius: 8px;
        padding: 10px;
        border: 1px solid #2a2e39;
        margin-bottom: 10px;
    }
    
    /* Signal Boxen */
    .signal-box { 
        font-size: 1.1em; 
        font-weight: 800; 
        text-align: center; 
        padding: 8px; 
        border-radius: 4px; 
        margin-top: 5px;
        color: #000;
        text-shadow: 0px 0px 1px rgba(255,255,255,0.5);
    }
    
    /* Forex Factory Impact Styles */
    .ff-high { border-left: 4px solid #ff4b4b; padding-left: 8px; margin-bottom: 4px; font-size: 0.85em; }
    .ff-med { border-left: 4px solid #ffa500; padding-left: 8px; margin-bottom: 4px; font-size: 0.85em; }
    .ff-low { border-left: 4px solid #f0e68c; padding-left: 8px; margin-bottom: 4px; font-size: 0.85em; }
    
    .pair-name { color: #d1d4dc; font-weight: bold; font-size: 1em; text-align: center; }
    
    /* Links */
    a { color: #2962ff !important; text-decoration: none; }
    
    .last-update { font-size: 0.7em; color: #787b86; text-align: center; margin-top: 30px; }
</style>
""", unsafe_allow_html=True)

# --- 1. DATEN HOLEN (Forex Factory Logik) ---
@st.cache_data(ttl=180, show_spinner=False)
def fetch_calendar_data():
    urls = [
        "https://www.investing.com/rss/news_25.rss", 
        "https://www.investing.com/rss/forex_news.rss",
        "https://www.fxstreet.com/rss/news",
        "https://cointelegraph.com/rss"
    ]
    
    events = []
    high_impact_keywords = ["cpi", "nfp", "gdp", "fomc", "rate decision", "interest rate", "payroll", "inflation"]
    
    for url in urls:
        try:
            f = feedparser.parse(url)
            for e in f.entries[:25]:
                title = e.title
                link = e.link
                lower = title.lower()
                
                # Impact bestimmen
                impact = "low"
                for k in high_impact_keywords:
                    if k in lower: impact = "high"
                
                # Signal bestimmen
                signal_score = 0
                signal_text = "News"
                
                if "beat" in lower or "above forecast" in lower or "stronger" in lower or "hike" in lower or "jump" in lower:
                    signal_score = 1
                    signal_text = "Bullish (Strong Data)"
                elif "miss" in lower or "below forecast" in lower or "weaker" in lower or "cut" in lower or "drop" in lower:
                    signal_score = -1
                    signal_text = "Bearish (Weak Data)"
                
                events.append({
                    "title": title,
                    "link": link,
                    "impact": impact,
                    "score": signal_score,
                    "signal_text": signal_text,
                    "raw": lower
                })
        except: continue
    return events

# --- 2. ANALYSE PRO PAAR ---
def analyze_pair(name, events):
    parts = name.replace(' (Gold)', '').split('/')
    base = parts[0].lower()
    quote = parts[1].lower() if len(parts) > 1 else ""
    
    if "XAU" in name: base = "gold"
    if "US30" in name: base = "dow"
    if "BTC" in name: base = "bitcoin"
    if "ADA" in name: base = "cardano"
    
    score = 0
    relevant_news = []
    
    for e in events:
        is_relevant = False
        if base in e["raw"]: is_relevant = True
        if quote in e["raw"]: is_relevant = True
        if "market" in e["raw"]: is_relevant = True
        
        if is_relevant:
            score += e["score"]
            if e["score"] != 0 or e["impact"] == "high":
                relevant_news.append(e)
            
    decision = "NEUTRAL"
    color = "#b2b5be" # Grau
    
    if score >= 1:
        decision = "KAUFEN"
        color = "#00ff00" # Grün
    elif score <= -1:
        decision = "VERKAUFEN"
        color = "#ff4b4b" # Rot
        
    return decision, color, relevant_news

# --- 3. IP FÜR QR CODE ---
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    local_ip = s.getsockname()[0]
    s.close()
    network_url = f"http://{local_ip}:8501"
except: network_url = "http://localhost:8501"


# --- 4. LAYOUT ---
st.title("📅 TradingView & Forex Factory Master")

cached_data = fetch_calendar_data()

# HIER WAR DER FEHLER: Jetzt sicher untereinander formatiert
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

st.subheader("🤖 KI-Scanner: Forecast vs. Actual")
for i in range(0, len(pairs), 4):
    cols = st.columns(4)
    for j, (name, ticker) in enumerate(pairs[i:i+4]):
        decision, color, news = analyze_pair(name, cached_data)
        
        with cols[j]:
            st.markdown(f"<div class='pair-name'>{name}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='signal-box' style='background-color: {color};'>{decision}</div>", unsafe_allow_html=True)
            
            with st.expander("News & Impact"):
                if news:
                    for n in news[:3]:
                        css_class = "ff-high" if n["impact"] == "high" else "ff-med"
                        st.markdown(f"<div class='{css_class}'><a href='{n['link']}'>{n['title']}</a></div>", unsafe_allow_html=True)
                else:
                    st.caption("Keine Signale.")

st.divider()

st.subheader("📊 Der Offizielle Wirtschaftskalender")
st.write("Vergleiche hier die Signale von oben mit den harten Zahlen.")

components.html("""
<div class="tradingview-widget-container">
  <div class="tradingview-widget-container__widget"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-events.js" async>
  {
  "colorTheme": "dark",
  "isTransparent": false,
  "width": "100%",
  "height": "800",
  "locale": "de_DE",
  "importanceFilter": "-1,0,1",
  "currencyFilter": "USD,EUR,JPY,GBP,AUD,CAD,CHF,CNY"
}
  </script>
</div>
""", height=800)

with st.sidebar:
    st.header("📱 Handy Link")
    st.image(f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={network_url}")
    st.write(f"`{network_url}`")
    st.info("Scanner & Kalender in einer App.")

st.markdown(f"<div class='last-update'>Live Logic | Auto-Refresh 3 Min | Zeit: {datetime.datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)

time.sleep(180) 
st.rerun()
