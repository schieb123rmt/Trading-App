import streamlit as st
import feedparser
from textblob import TextBlob
import datetime
from datetime import timedelta
import time
import socket
import streamlit.components.v1 as components

# 1. Konfiguration
st.set_page_config(page_title="Trading ATM Future", layout="wide")

# CSS: Design Anpassung (Genau wie dein Screenshot)
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
    
    /* SIGNAL BOX (Kaufen/Verkaufen) */
    .signal-box { 
        font-size: 1.1em; font-weight: 800; text-align: center; 
        padding: 8px; border-radius: 4px; margin-top: 5px; margin-bottom: 10px;
        color: #000; text-shadow: 0px 0px 1px rgba(255,255,255,0.5);
    }
    
    /* --- NEU: DIE GOLDENE WARN-BOX (Wie im Screenshot) --- */
    .future-warning {
        border: 2px solid #ffd700;       /* Goldener Rand */
        background-color: #332b00;       /* Dunkler, gelblicher Hintergrund */
        color: #ffd700;                  /* Goldene Schrift */
        padding: 10px; 
        border-radius: 6px; 
        font-size: 0.9em; 
        margin-top: 5px; 
        margin-bottom: 10px;
        text-align: center; 
        font-weight: bold;
        line-height: 1.4;
        box-shadow: 0 0 10px rgba(255, 215, 0, 0.1); /* Leichtes Leuchten */
    }
    
    .warning-header {
        text-transform: uppercase;
        font-size: 0.85em;
        margin-bottom: 4px;
        opacity: 0.9;
    }
    
    /* News Styles */
    .ff-high { border-left: 4px solid #ff4b4b; padding-left: 8px; margin-bottom: 6px; font-size: 0.85em; }
    .ff-med { border-left: 4px solid #ffa500; padding-left: 8px; margin-bottom: 6px; font-size: 0.85em; }
    .ff-low { border-left: 4px solid #4caf50; padding-left: 8px; margin-bottom: 6px; font-size: 0.85em; color: #aaa; }
    
    .pair-name { color: #d1d4dc; font-weight: bold; font-size: 1em; text-align: center; }
    a { color: #2962ff !important; text-decoration: none; }
    
    .last-update { font-size: 0.7em; color: #787b86; text-align: center; margin-top: 30px; }
</style>
""", unsafe_allow_html=True)

# --- HELPER: SYNONYME (Damit wir alles finden) ---
def get_keywords_for_currency(symbol):
    symbol = symbol.upper()
    keywords = [symbol]
    if symbol == "USD": keywords.extend(["dollar", "greenback", "fed ", "fomc", "powell", "treasury"])
    if symbol == "EUR": keywords.extend(["euro", "ecb", "lagarde", "ez ", "german"])
    if symbol == "GBP": keywords.extend(["pound", "sterling", "boe ", "bailey", "uk economy"])
    if symbol == "JPY": keywords.extend(["yen", "boj ", "ueda", "japan"])
    if symbol == "CHF": keywords.extend(["franc", "snb ", "swiss"])
    if symbol == "CAD": keywords.extend(["loonie", "boc ", "canada", "oil"])
    if symbol == "AUD": keywords.extend(["aussie", "rba ", "australia"])
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

# --- 1. DATEN HOLEN ---
@st.cache_data(ttl=300, show_spinner=False)
def fetch_calendar_data():
    urls = [
        "https://www.investing.com/rss/news_25.rss", 
        "https://www.fxstreet.com/rss/news",
        "https://cointelegraph.com/rss"
    ]
    
    events = []
    # Wörter die auf MORGEN/ZUKUNFT hindeuten
    future_keywords = ["preview", "outlook", "forecast", "tomorrow", "week ahead", "projection", "expects", "likely to"]
    high_impact_keywords = ["cpi", "nfp", "gdp", "fomc", "rate decision", "interest rate", "inflation"]
    
    for url in urls:
        try:
            f = feedparser.parse(url)
            for e in f.entries[:50]: # 50 News pro Feed scannen
                title = e.title
                link = e.link
                lower = title.lower()
                
                impact = "low"
                for k in high_impact_keywords:
                    if k in lower: impact = "high"
                
                # Check: Ist es eine Prognose für die Zukunft?
                is_future = False
                for k in future_keywords:
                    if k in lower: is_future = True
                
                # Signal Bestimmung
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

# --- 2. ANALYSE PRO PAAR ---
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
            # Score Berechnung (nur aktuelle Fakten zählen sofort)
            if not e["is_future"]:
                score += e["score"]
            
            #
