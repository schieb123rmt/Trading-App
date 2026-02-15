import streamlit as st
import feedparser
from textblob import TextBlob
import datetime
import time
import socket
import streamlit.components.v1 as components

# 1. Konfiguration
st.set_page_config(page_title="Trading ATM Turbo", layout="wide")

# CSS: Design Anpassungen
st.markdown("""
<style>
    div[data-testid="column"] {
        background-color: #1e1e1e;
        border-radius: 12px;
        padding: 15px;
        border: 1px solid #333;
        margin-bottom: 20px;
        transition: transform 0.2s;
    }
    div[data-testid="column"]:hover {
        border-color: #4da6ff;
        transform: translateY(-2px);
    }
    .icon-container { position: relative; width: 80px; height: 60px; margin: 0 auto 10px; }
    .icon-1 { width: 45px; height: 45px; border-radius: 50%; position: absolute; left: 0; top: 0; background-size: cover; z-index: 2; border: 2px solid #1e1e1e; }
    .icon-2 { width: 45px; height: 45px; border-radius: 50%; position: absolute; left: 28px; top: 12px; background-size: cover; z-index: 1; border: 2px solid #1e1e1e; }
    .pair-title { font-size: 1.1em; font-weight: bold; color: white; text-align: center; margin-bottom: 5px; }
    .status-row { display: flex; justify-content: space-between; font-size: 0.9em; margin-bottom: 10px; border-bottom: 1px solid #333; padding-bottom: 5px;}
    a { color: #4da6ff !important; text-decoration: none; font-size: 0.85em; }
    .news-title { font-weight: 600; color: #eee; margin-bottom: 2px; line-height: 1.3; font-size: 0.9em; }
    .last-update { font-size: 0.8em; color: #555; text-align: center; margin-top: 30px; }
</style>
""", unsafe_allow_html=True)

# Funktionen (Icons & Chart Status)
def get_icon_url(c):
    crypto = {"BTC": "https://cryptologos.cc/logos/bitcoin-btc-logo.png", "ADA": "https://cryptologos.cc/logos/cardano-ada-logo.png", "XAU": "https://cdn-icons-png.flaticon.com/512/272/272530.png"}
    if c.upper() in crypto: return crypto[c.upper()]
    m = {"USD":"us","JPY":"jp","EUR":"eu","GBP":"gb","CHF":"ch","CAD":"ca","AUD":"au","US30":"us"}
    return f"https://flagcdn.com/w160/{m.get(c.upper(), 'un')}.png"

def get_chart_icon(status):
    if status == "STEIGEND": return "https://cdn-icons-png.flaticon.com/512/2966/2966334.png"
    if status == "FALLEND": return "https://cdn-icons-png.flaticon.com/512/2966/2966327.png"
    return "https://cdn-icons-png.flaticon.com/512/25/25181.png"

# --- TURBO-MODUS: ZENTRALES CACHING ---
# Wir laden ALLE News nur EINMAL alle 5 Minuten (300 Sekunden) herunter.
# Das verhindert, dass die App bei jedem Klick hängt.
@st.cache_data(ttl=300, show_spinner=False)
def fetch_all_news_central():
    urls = [
        "https://www.investing.com/rss/news_25.rss", # Wirtschaftskalender Events
        "https://www.investing.com/rss/forex_news.rss",
        "https://www.fxstreet.com/rss/news",
        "https://cointelegraph.com/rss"
    ]
    
    all_articles = []
    
    for url in urls:
        try:
            f = feedparser.parse(url)
            for e in f.entries[:20]: # Max 20 pro Feed
                all_articles.append({
                    "title": e.title,
                    "link": e.link,
                    "lower_title": e.title.lower()
                })
        except:
            continue
            
    return all_articles

# Die optimierte Analyse-Funktion greift nun auf den Cache zu
def analyze_fast(name, cached_articles):
    search_term = name.split('/')[0].lower()
    if "XAU" in name: search_term = "gold"
    if "US30" in name: search_term = "dow"
    
    score, count, found_news = 0, 0, []
    
    # Event-Logik (Forex Factory Style)
    calendar_signals = {
        "beat": 2.0, "beating": 2.0, "above estimate": 2.0, "stronger": 2.0, 
        "miss": -2.0, "missing": -2.0, "below estimate": -2.0, "weaker": -2.0,
        "hike": 1.5, "cut": -1.5, "rise": 1.0, "fall": -1.0
    }
    sentiment_words = {
        "bullish": 0.5, "gain": 0.5, "uptrend": 0.5, "high": 0.4,
        "bearish": -0.5, "loss": -0.5, "downtrend": -0.5, "low": -0.4
    }

    # Wir iterieren durch die BEREITS GELADENEN Artikel (kein Download mehr hier!)
    for article in cached_articles:
        title_lower = article["lower_title"]
        
        # Relevanz-Check
        is_relevant = False
        if search_term in title_lower: is_relevant = True
        if "market" in title_lower: is_relevant = True
        if "dollar" in title_lower and ("usd" in name.lower() or "xau" in name.lower()): is_relevant = True
        
        if is_relevant:
            val = TextBlob(article["title"]).sentiment.polarity
            
            # Event Check
            event_found = False
            for word, weight in calendar_signals.items():
                if word in title_lower: 
                    val += weight
                    event_found = True
            
            if not event_found:
                for word, weight in sentiment_words.items():
                    if word in title_lower: val += weight
            
            score += val
            count += 1
            
            prefix = "⚡ EVENT: " if event_found else ""
            found_news.append((prefix + article["title"], article["link"]))

    avg = score / count if count > 0 else 0
    if avg > 0.1: return "STEIGEND", "#00ff00", round(abs(avg)*100, 2), found_news
    if avg < -0.1: return "FALLEND", "#ff4b4b", round(abs(avg)*100, 2), found_news
    return "NEUTRAL", "#ffa500", 0.0, found_news

# --- IP ADRESSE FÜR QR CODE ERMITTELN ---
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    local_ip = s.getsockname()[0]
    s.close()
    network_url = f"http://{local_ip}:8501"
except:
    network_url = "http://localhost:8501"


# --- LAYOUT START ---
st.title("🚀 Trading ATM Turbo")

# Zentrale Daten laden (Passiert nur 1x alle 5 Min!)
with st.spinner('Lade Finanzdaten...'):
    all_cached_news = fetch_all_news_central()

# Sidebar mit QR Code für Handy
with st.sidebar:
    st.header("📱 Handy Zugang")
    st.write("Scanne diesen Code mit deiner Handy-Kamera, um die App im WLAN zu öffnen:")
    # Wir nutzen eine externe API für den QR Code, damit du nichts installieren musst
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={network_url}"
    st.image(qr_url)
    st.write(f"Oder tippe: `{network_url}`")
    st.info("💡 Beide Geräte müssen im selben WLAN sein!")

# Tab-System
tab1, tab2 = st.tabs(["⚡ Live Event-Scanner", "📅 Kalender Übersicht"])

with tab1:
    pairs = [
        ("USD/JPY", "USDJPY=X"), ("CHF/JPY", "CHFJPY=X"), ("EUR/JPY", "EURJPY=X"),
        ("EUR/GBP", "EURGBP=X"), ("GBP/JPY", "GBPJPY=X"), ("USD/CAD", "USDCAD=X"),
        ("US30", "^DJI"), ("XAU/USD", "GC=F"), ("EUR/USD", "EURUSD=X"),
        ("GBP/CAD", "GBPCAD=X"), ("EUR/CHF", "EURCHF=X"), ("USD/CHF", "USDCHF=X"),
        ("BTC/USD", "BTC-USD"), ("ADA/USDT", "ADA-USD")
    ]
    
    for i in range(0, len(pairs), 4):
        cols = st.columns(4)
        for j, (name, ticker) in enumerate(pairs[i:i+4]):
            # Hier nutzen wir die SCHNELLE Funktion
            status, color, impact, news_list = analyze_fast(name, all_cached_news)
            parts = name.replace(' (Gold)', '').split('/')
            
            with cols[j]:
                b_url = get_icon_url(parts[0])
                q_url = get_icon_url(parts[1] if len(parts)>1 else "USD")
                
                st.markdown(f"""
                    <div class="icon-container">
                        <div class="icon-1" style="background-image: url('{b_url}');"></div>
                        <div class="icon-2" style="background-image: url('{q_url}');"></div>
                    </div>
                    <div class="pair-title">{name}</div>
                    <div class="status-row">
                        <div style="color: {color}; font-weight:bold;">
                            <img src="{get_chart_icon(status)}" width="20"> {status}
                        </div>
                        <div style="color:#bbb;">{impact}%</div>
                    </div>
                """, unsafe_allow_html=True)
                
                with st.expander(f"Infos ({len(news_list)})"):
                    if news_list:
                        for title, link in news_list[:5]:
                            title_html = title.replace("⚡ EVENT:", "<span style='color: #ffd700; font-weight:bold;'>⚡ EVENT:</span>")
                            st.markdown(f"<div class='news-title'>{title_html}</div>", unsafe_allow_html=True)
                            st.markdown(f"[🔗 Quelle]({link})")
                            st.markdown("---")
                    else: st.caption("Keine Events.")

with tab2:
    st.header("Wirtschaftskalender")
    components.html("""
    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-events.js" async>
      {
      "colorTheme": "dark", "isTransparent": false, "width": "100%", "height": "800",
      "locale": "de_DE", "importanceFilter": "-1,0,1", "currencyFilter": "USD,EUR,JPY,GBP,AUD,CAD,CHF"
    }
      </script>
    </div>
    """, height=800)

st.markdown(f"<div class='last-update'>High-Performance Mode | Nächster News-Download in 5 Min | Zeit: {datetime.datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)

time.sleep(30)
st.rerun()