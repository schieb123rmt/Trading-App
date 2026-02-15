import streamlit as st
import feedparser
from textblob import TextBlob
import datetime
import time
import socket
import streamlit.components.v1 as components

# 1. Konfiguration
st.set_page_config(page_title="TradingView Calendar Master", layout="wide")

# CSS: TradingView & Forex Factory Style
st.markdown("""
<style>
    div[data-testid="column"] {
        background-color: #131722; /* TradingView Dark Background */
        border-radius: 8px;
        padding: 10px;
        border: 1px solid #363c4e;
    }
    .main-header { font-size: 1.5em; font-weight: bold; color: #d1d4dc; margin-bottom: 10px; }
    .signal-box { 
        font-size: 1.2em; 
        font-weight: 900; 
        text-align: center; 
        padding: 10px; 
        border-radius: 4px; 
        margin-top: 5px;
        color: black;
    }
    .ff-impact-high { border-left: 5px solid #ff4b4b; padding-left: 10px; margin-bottom: 5px; } /* Forex Factory Rot */
    .ff-impact-med { border-left: 5px solid #ffa500; padding-left: 10px; margin-bottom: 5px; } /* Forex Factory Orange */
    
    /* Angepasste Links */
    a { color: #2962ff !important; text-decoration: none; font-size: 0.8em; }
    
    .last-update { font-size: 0.7em; color: #787b86; text-align: center; margin-top: 20px; }
</style>
""", unsafe_allow_html=True)

# --- 1. DAS GEHIRN: FOREX FACTORY LOGIK ---
@st.cache_data(ttl=120, show_spinner=False) # Alle 2 Min Update
def fetch_calendar_news():
    # Wir nutzen Investing.com Kalender-Feed, da er ForexFactory am ähnlichsten ist
    # und maschinell lesbar ist (im Gegensatz zum TradingView Widget)
    urls = [
        "https://www.investing.com/rss/news_25.rss", # Wirtschaftskalender News
        "https://www.fxstreet.com/rss/news"
    ]
    
    all_events = []
    
    # Schlüsselwörter für TradingView/ForexFactory Events
    high_impact = ["cpi", "nfp", "gdp", "rate decision", "fomc", "interest rate", "unemployment"]
    
    for url in urls:
        try:
            f = feedparser.parse(url)
            for e in f.entries[:20]:
                title = e.title
                link = e.link
                lower_title = title.lower()
                
                # Impact Bestimmung (Forex Factory Style)
                impact = "Low"
                score = 0
                
                # Check High Impact
                for k in high_impact:
                    if k in lower_title: 
                        impact = "High"
                        
                # Check Prognose vs. Aktuell (Das ist die TradingView Spalte "Forecast")
                # Wenn wir Wörter wie "beats", "above", "misses" finden, wissen wir das Ergebnis
                signal = "Neutral"
                
                if "beat" in lower_title or "above forecast" in lower_title or "stronger" in lower_title:
                    signal = "Bullish (Besser als Prognose)"
                    score = 1
                elif "miss" in lower_title or "below forecast" in lower_title or "weaker" in lower_title:
                    signal = "Bearish (Schlechter als Prognose)"
                    score = -1
                elif "hike" in lower_title:
                    signal = "Rate Hike (Zinserhöhung)"
                    score = 1
                elif "cut" in lower_title:
                    signal = "Rate Cut (Zinssenkung)"
                    score = -1
                    
                all_events.append({
                    "title": title,
                    "link": link,
                    "impact": impact,
                    "signal": signal,
                    "score": score,
                    "raw": lower_title
                })
        except: continue
        
    return all_events

def analyze_pair_logic(name, events):
    # Filtert die globalen Events passend zum Währungspaar
    search_term = name.split('/')[0].lower() # z.B. "usd" bei "USD/JPY"
    if "XAU" in name: search_term = "gold"
    if "US30" in name: search_term = "dow"
    
    pair_score = 0
    relevant_news = []
    
    for event in events:
        # Relevanz prüfen
        is_relevant = False
        if search_term in event["raw"]: is_relevant = True
        if "market" in event["raw"]: is_relevant = True # Global
        if "dollar" in event["raw"] and "usd" in search_term: is_relevant = True
        
        if is_relevant:
            pair_score += event["score"]
            relevant_news.append(event)
            
    # Ergebnis
    if pair_score > 0: return "KAUFEN (Daten stark)", "#00ff00", relevant_news
    if pair_score < 0: return "VERKAUFEN (Daten schwach)", "#ff4b4b", relevant_news
    return "NEUTRAL (Warten)", "#ffa500", relevant_news


# --- 2. IP FINDER FÜR HANDY ---
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    local_ip = s.getsockname()[0]
    s.close()
    network_url = f"http://{local_ip}:8501"
except: network_url = "http://localhost:8501"


# --- 3. LAYOUT START ---
st.title("📅 TradingView Calendar Priority")

# Daten laden
cached_events = fetch_calendar_news()

# Oben: Die Signale (Das Ergebnis der Analyse)
st.subheader("🤖 KI-Analyse der Kalender-Daten")
pairs = [("EUR/USD", "EURUSD=X"), ("USD/JPY", "USDJPY=X"), ("GBP/USD", "GBPUSD=X"), ("XAU/USD", "GC=F"), ("US30", "^DJI")]

cols = st.columns(len(pairs))
for i, (name, ticker) in enumerate(pairs):
    decision, color, news = analyze_pair_logic(name, cached_events)
    with cols[i]:
        st.markdown(f"**{name}**")
        st.markdown(f"<div class='signal-box' style='background-color: {color};'>{decision}</div>", unsafe_allow_html=True)
        
        with st.expander("Quellen & Events"):
            if news:
                for n in news[:3]:
                    impact_color = "red" if n["impact"] == "High" else "orange"
                    st.markdown(f"<div style='border-left: 3px solid {impact_color}; padding-left:5px; font-size:0.8em;'>{n['title']}</div>", unsafe_allow_html=True)
            else:
                st.caption("Keine Abweichungen im Kalender.")

st.divider()

# Unten: Der TradingView Kalender (Das visuelle Herzstück)
st.subheader("📊 Der Offizielle TradingView Wirtschaftskalender")
st.caption("Nutze diese Tabelle, um die Signale oben zu bestätigen (Forecast vs. Actual).")

# Das ist das originale Widget von TradingView - Priorität 1
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

# Sidebar
with st.sidebar:
    st.header("📱 Handy Link")
    st.image(f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={network_url}")
    st.write("Scan mich!")

st.markdown(f"<div class='last-update'>Quellen: TradingView Widget + Investing/ForexFactory Logic | Zeit: {datetime.datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)

time.sleep(60) # Auto-Refresh jede Minute
st.rerun()
