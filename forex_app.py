import streamlit as st
import feedparser
from textblob import TextBlob
import datetime
from datetime import timedelta
import time
import socket
import streamlit.components.v1 as components

# 1. Konfiguration
st.set_page_config(page_title="Trading ATM Ultimate Pro", layout="wide")

# 2. CSS STYLING (Vollständiges Design-Paket)
st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    
    /* Container für die Paare */
    div[data-testid="column"] {
        background-color: #1e222d;
        border-radius: 8px;
        padding: 10px;
        border: 1px solid #2a2e39;
        margin-bottom: 10px;
    }
    
    /* ICON CONTAINER (Die überlappenden Kreise) */
    .icon-container { position: relative; width: 80px; height: 50px; margin: 0 auto 5px; }
    .icon-1 { width: 40px; height: 40px; border-radius: 50%; position: absolute; left: 10px; top: 0; background-size: cover; z-index: 2; border: 2px solid #1e222d; }
    .icon-2 { width: 40px; height: 40px; border-radius: 50%; position: absolute; left: 35px; top: 10px; background-size: cover; z-index: 1; border: 2px solid #1e222d; }
    
    /* SIGNAL BOX */
    .signal-box { 
        font-size: 1.1em; font-weight: 800; text-align: center; 
        padding: 8px; border-radius: 4px; margin-top: 5px; margin-bottom: 10px;
        color: #000; text-shadow: 0px 0px 1px rgba(255,255,255,0.5);
    }
    
    /* GOLDENE WARN-BOX (Morgen/Vorschau) */
    .future-warning {
        border: 2px solid #ffd700;
        background-color: #332b00;
        color: #ffd700;
        padding: 10px; 
        border-radius: 6px; 
        font-size: 0.85em; 
        margin-top: 5px; 
        margin-bottom: 8px;
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
    
    /* SCROLLBOX FÜR NEWS (Das Herzstück) */
    .news-scroll-container {
        max-height: 220px;
        overflow-y: auto;
        padding-right: 5px;
        margin-top: 5px;
        background-color: #161a25;
        padding: 8px;
        border-radius: 4px;
        border: 1px solid #2a2e39;
    }
    
    /* Scrollbar Styling */
    .news-scroll-container::-webkit-scrollbar { width: 6px; }
    .news-scroll-container::-webkit-scrollbar-track { background: #161a25; }
    .news-scroll-container::-webkit-scrollbar-thumb { background-color: #444; border-radius: 10px; }

    /* News Items Styles */
    .ff-high { border-left: 3px solid #ff4b4b; padding-left: 8px; margin-bottom: 8px; font-size: 0.85em; line-height: 1.3; }
    .ff-med { border-left: 3px solid #ffa500; padding-left: 8px; margin-bottom: 8px; font-size: 0.85em; line-height: 1.3; }
    .ff-low { border-left: 3px solid #4caf50; padding-left: 8px; margin-bottom: 8px; font-size: 0.85em; line-height: 1.3; color: #aaa; }
    
    .pair-name { color: #d1d4dc; font-weight: bold; font-size: 1.1em; text-align: center; margin-top: 5px; }
    a { color: #4da6ff !important; text-decoration: none; }
    a:hover { text-decoration: underline; color: #80bfff !important; }
    
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

# 4. HELPER: SYNONYME (Suche verbessern)
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
    if symbol == "BTC": keywords.extend(["bitcoin", "crypto", "sec ", "etf"])
    if symbol == "XAU": keywords.extend(["gold", "bullion", "metal"])
    if symbol == "US30": keywords.extend(["dow", "wall street", "stocks", "sp500"])
    return keywords

# 5. HELPER: KALENDER EINTAG
def create_ics(event_title, description):
    tomorrow = datetime.datetime.now() + timedelta(days=1)
    start_time = tomorrow.replace(hour=9, minute=0, second=0).strftime('%Y%m%dT%H%M%S')
    end_time = tomorrow.replace(hour=10, minute=0, second=0).strftime('%Y%m%dT%H%M%S')
    ics_content = f"BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//Trading ATM//Future Scanner//EN\nBEGIN:VEVENT\nUID:{int(time.time())}@tradingatm.app\nDTSTAMP:{datetime.datetime.now().strftime('%Y%m%dT%H%M%S')}\nDTSTART:{start_time}\nDTEND:{end_time}\nSUMMARY:⚡ Markt-Vorschau: {event_title}\nDESCRIPTION:{description}\nBEGIN:VALARM\nTRIGGER:-PT15M\nACTION:DISPLAY\nDESCRIPTION:Reminder\nEND:VALARM\nEND:VEVENT\nEND:VCALENDAR"
    return ics_content

# 6. DATEN LADEN
@st.cache_data(ttl=300, show_spinner=False)
def fetch_calendar_data():
    urls = ["https://www.investing.com/rss/news_25.rss", "https://www.fxstreet.com/rss/news", "https://cointelegraph.com/rss"]
    events = []
    high_impact = ["cpi", "nfp", "gdp", "fomc", "rate decision", "interest rate", "inflation"]
    future_words = ["preview", "outlook", "forecast", "tomorrow", "week ahead", "projection", "expects"]
    for url in urls:
        try:
            f = feedparser.parse(url)
            for e in f.entries[:50]:
                title, link, lower = e.title, e.link, e.title.lower()
                impact = "high" if any(k in lower for k in high_impact) else "low"
                is_future = any(k in lower for k in future_words)
                score = 1 if any(k in lower for k in ["beat", "above", "stronger", "hike", "bullish"]) else -1 if any(k in lower for k in ["miss", "below", "weaker", "cut", "bearish"]) else 0
                events.append({"title": title, "link": link, "impact": impact, "score": score, "is_future": is_future, "raw": lower})
        except: continue
    return events

# 7. ANALYSE LOGIK
def analyze_pair(name, events):
    parts = name.replace(' (Gold)', '').split('/')
    base_sym, quote_sym = parts[0], parts[1] if len(parts) > 1 else ""
    if "XAU" in name: base_sym = "XAU"
    if "US30" in name: base_sym = "US30"
    if "BTC" in name: base_sym = "BTC"
    
    base_keywords = get_keywords_for_currency(base_sym)
    quote_keywords = get_keywords_for_currency(quote_sym) if quote_sym else []
    score, relevant_news, future_warning = 0, [], None
    
    for e in events:
        if any(k in e["raw"] for k in base_keywords) or any(k in e["raw"] for k in quote_keywords) or "market" in e["raw"]:
            if not e["is_future"]: score += e["score"]
            if e["is_future"]:
                if future_warning is None or (e["impact"] == "high" and future_warning["impact"] != "high"):
                    future_warning = e
            relevant_news.append(e)
            
    decision, color = ("KAUFEN", "#00ff00") if score >= 1 else ("VERKAUFEN", "#ff4b4b") if score <= -1 else ("NEUTRAL", "#b2b5be")
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
st.title("💹 Trading ATM Pro")
tomorrow_date = (datetime.datetime.now() + timedelta(days=1)).strftime('%d.%m.%Y')
st.caption(f"Live Sentiment Scanner | Vorschau für Morgen ({tomorrow_date})")

cached_data = fetch_calendar_data()

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
        decision, color, news, future_alert = analyze_pair(name, cached_data)
        parts = name.replace(' (Gold)', '').split('/')
        b_url, q_url = get_icon_url(parts[0]), get_icon_url(parts[1] if len(parts)>1 else "USD")
        if "XAU" in name: b_url = get_icon_url("XAU")
        if "BTC" in name: b_url = get_icon_url("BTC")
        if "ADA" in name: b_url = get_icon_url("ADA")
        if "US30" in name: b_url = get_icon_url("US30")
        
        with cols[j]:
            st.markdown(f'<div class="icon-container"><div class="icon-1" style="background-image: url(\'{b_url}\');"></div><div class="icon-2" style="background-image: url(\'{q_url}\');"></div></div><div class="pair-name">{name}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="signal-box" style="background-color: {color};">{decision}</div>', unsafe_allow_html=True)
            
            if future_alert:
                st.markdown(f'<div class="future-warning"><div class="warning-header">⚠️ VORSCHAU/MORGEN:</div>{future_alert["title"]}</div>', unsafe_allow_html=True)
                ics_data = create_ics(f"{name}: {future_alert['title']}", f"Link: {future_alert['link']}")
                st.download_button("📅 Termin speichern", ics_data, f"event_{name}.ics", "text/calendar", key=f"btn_{i}_{j}")

            with st.expander(f"News ({len(news)})"):
                if news:
                    news.sort(key=lambda x: (x["impact"] == "high", x["is_future"]), reverse=True)
                    # WICHTIG: Hier bauen wir NUR den HTML String und geben ihn EINMAL aus
                    news_html = "<div class='news-scroll-container'>"
                    for n in news:
                        icon = "🔮" if n["is_future"] else "🔥" if n["impact"] == "high" else "📄"
                        css = "ff-high" if n["impact"] == "high" else "ff-med"
                        news_html += f"<div class='{css}'>{icon} <a href='{n['link']}' target='_blank'>{n['title']}</a></div>"
                    news_html += "</div>"
                    st.markdown(news_html, unsafe_allow_html=True)
                else:
                    st.caption("Keine News.")

st.divider()
st.subheader("📊 Offizieller Kalender")
components.html('<div class="tradingview-widget-container"><div class="tradingview-widget-container__widget"></div><script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-events.js" async>{ "colorTheme": "dark", "isTransparent": false, "width": "100%", "height": "600", "locale": "de_DE", "importanceFilter": "-1,0,1" }</script></div>', height=600)

with st.sidebar:
    st.header("📱 Handy Link")
    st.image(f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={network_url}")
    st.write(f"Netzwerk-URL: `{network_url}`")

st.markdown(f"<div class='last-update'>Live Logic | Auto-Refresh 5 Min | Zeit: {datetime.datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)
time.sleep(300) 
st.rerun()
