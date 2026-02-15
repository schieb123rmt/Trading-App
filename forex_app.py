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
        background-color: #1e222d; /* TradingView Box Farbe */
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
    
    /* Forex Factory Impact Styles für die News-Liste */
    .ff-high { border-left: 4px solid #ff4b4b; padding-left: 8px; margin-bottom: 4px; font-size: 0.85em; }
    .ff-med { border-left: 4px solid #ffa500; padding-left: 8px; margin-bottom: 4px; font-size: 0.85em; }
    .ff-low { border-left: 4px solid #f0e68c; padding-left: 8px; margin-bottom: 4px; font-size: 0.85em; }
    
    .pair-name { color: #d1d4dc; font-weight: bold; font-size: 1em; text-align: center; }
    
    /* Links */
    a { color: #2962ff !important; text-decoration: none; }
    
    .last-update { font-size: 0.7em; color: #787b86; text-align: center; margin-top: 30px; }
</style>
""", unsafe_allow_html=True)

# --- 1. DATEN HOLEN (Forex Factory Logik via Investing.com RSS) ---
@st.cache_data(ttl=180, show_spinner=False)
def fetch_calendar_data():
    # Wir nutzen Feeds, die über Forecasts berichten
    urls = [
        "https://www.investing.com/rss/news_25.rss", # Wirtschaftskalender Events
        "https://www.investing.com/rss/forex_news.rss",
        "https://www.fxstreet.com/rss/news",
        "https://cointelegraph.com/rss"
    ]
    
    events = []
    
    # Schlüsselwörter für Forex Factory Impact
    high_impact_keywords = ["cpi", "nfp", "gdp", "fomc", "rate decision", "interest rate", "payroll", "inflation"]
    
    for url in urls:
        try:
            f = feedparser.parse(url)
            for e in f.entries[:25]:
                title = e.title
                link = e.link
                lower = title.lower()
                
                # 1. Impact bestimmen
                impact = "low"
                for k in high_impact_keywords:
                    if k in lower: impact = "high"
                
                # 2. Signal bestimmen (Forecast vs Actual)
                signal_score = 0
                signal_text = "News"
                
                # Bullish Wörter (Besser als erwartet / Hike)
                if "beat" in lower or "above forecast" in lower or "stronger" in lower or "hike" in lower or "jump" in lower:
                    signal_score = 1
                    signal_text = "Bullish (Strong Data)"
                
                # Bearish Wörter (Schlechter als erwartet / Cut)
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
    # Währung aufsplitten (z.B. EUR/USD -> sucht nach EUR und USD News)
    parts = name.replace(' (Gold)', '').split('/')
    base = parts[0].lower() # eur
    quote = parts[1].lower() if len(parts) > 1 else "" # usd
    
    if "XAU" in name: base = "gold"
    if "US30" in name: base = "dow"
    if "BTC" in name: base = "bitcoin"
    if "ADA" in name: base = "cardano"
    
    score = 0
    relevant_news = []
    
    for e in events:
        is_relevant = False
        # Ist die News für eine der beiden Währungen relevant?
        if base in e["raw"]: is_relevant = True
        if quote in e["raw"]: is_relevant = True
        if "market" in e["raw"]: is_relevant = True # Globale News
        
        if is_relevant:
            score += e["score"]
            # Nur relevante News anzeigen
            if e["score"] != 0 or e["impact"] == "high":
                relevant_news.append(e)
            
    # Entscheidung
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

# Cache laden
cached_data = fetch_calendar_data()

# DIE KOMPLETTE LISTE (14 Paare)
pairs = [
    ("USD/JPY", "USDJPY=X"), ("CHF/JPY", "CHFJPY
