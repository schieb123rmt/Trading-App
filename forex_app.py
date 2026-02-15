import streamlit as st
import feedparser
from textblob import TextBlob
import datetime
from datetime import timedelta
import time
import socket
import streamlit.components.v1 as components

# 1. Konfiguration
st.set_page_config(page_title="Trading ATM Impact Master", layout="wide")

# 2. CSS STYLING
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
    .icon-container { position: relative; width: 80px; height: 50px; margin: 0 auto 5px; }
    .icon-1 { width: 40px; height: 40px; border-radius: 50%; position: absolute; left: 10px; top: 0; background-size: cover; z-index: 2; border: 2px solid #1e222d; }
    .icon-2 { width: 40px; height: 40px; border-radius: 50%; position: absolute; left: 35px; top: 10px; background-size: cover; z-index: 1; border: 2px solid #1e222d; }
    .signal-box { 
        font-size: 1.1em; font-weight: 800; text-align: center; 
        padding: 8px; border-radius: 4px; margin-top: 5px; margin-bottom: 10px;
        color: #000; text-shadow: 0px 0px 1px rgba(255,255,255,0.5);
    }
    .future-warning {
        border: 2px solid #ffd700; background-color: #332b00; color: #ffd700;
        padding: 10px; border-radius: 6px; font-size: 0.85em; margin-bottom: 8px;
        text-align: center; font-weight: bold; line-height: 1.4;
    }
    .warning-header { text-transform: uppercase; font-size: 0.9em; margin-bottom: 5px; text-decoration: underline; }
    
    .news-scroll-container {
        max-height: 220px; overflow-y: auto; padding-right: 5px;
        margin-top: 5px; background-color: #161a25; padding: 8px; border-radius: 4px; border: 1px solid #2a2e39;
    }
    .news-scroll-container::-webkit-scrollbar { width: 6px; }
    .news-scroll-container::-webkit-scrollbar-thumb { background-color: #444; border-radius: 10px; }

    .ff-high { border-left: 3px solid #ff4b4b; padding-left: 8px; margin-bottom: 10px; font-size: 0.85em; }
    .news-date { font-size: 0.75em; color: #666; display: block; margin-top: 2px; }
    
    .pair-name { color: #d1d4dc; font-weight: bold; font-size: 1.1em; text-align: center; margin-top: 5px; }
    a { color: #4da6ff !important; text-decoration: none; }
    .last-update { font-size: 0.7em; color: #787b86; text-align: center; margin-top: 30px; }
</style>
""", unsafe_allow_html=True)

# 3. HELPER FUNKTIONEN
def get_icon_url(c):
    crypto = {"BTC": "https://cryptologos.cc/logos/bitcoin-btc-logo.png", "ADA": "https://cryptologos.cc/logos/cardano-ada-logo.png", "XAU": "https://cdn-icons-png.flaticon.com/512/272/272530.png"}
    if c.upper() in crypto: return crypto[c.upper()]
    m = {"USD":"us","JPY":"jp","EUR":"eu","GBP":"gb","CHF":"ch","CAD":"ca","AUD":"au","US30":"us"}
    return f"https://flagcdn.com/w160/{m.get(c.upper(), 'un')}.png"

def get_keywords_for_currency(symbol):
    symbol = symbol.upper()
    keywords = [symbol]
    if symbol == "USD": keywords.extend(["dollar", "fed ", "fomc", "powell"])
    if symbol == "EUR": keywords.extend(["euro", "ecb", "lagarde"])
    if symbol == "GBP": keywords.extend(["pound", "sterling", "boe "])
    if symbol == "JPY": keywords.extend(["yen", "boj "])
    if symbol == "XAU": keywords.extend(["gold", "bullion"])
    if symbol == "US30": keywords.extend(["dow", "wall street", "stocks"])
    return keywords

def create_ics(event_title, description):
    tomorrow = datetime.datetime.now() + timedelta(days=1)
    start_time = tomorrow.replace(hour=9, minute=0, second=0).strftime('%Y%m%dT%H%M%S')
    ics_content = f"BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\nSUMMARY:⚡ {event_title}\nDTSTART:{start_time}\nDESCRIPTION:{description}\nEND:VEVENT\nEND:VCALENDAR"
    return ics_content

# 4. DATEN LADEN & IMPACT FILTER
@st.cache_data(ttl=300, show_spinner=False)
def fetch_calendar_data():
    urls = ["https://www.investing.com/rss/news_25.rss", "https://www.fxstreet.com/rss/news"]
    events = []
    high_impact_list = ["cpi", "nfp", "gdp", "fomc", "rate", "interest", "inflation", "payroll", "fed", "ecb", "boj"]
    future_words = ["preview", "outlook", "forecast", "tomorrow", "week ahead"]
    
    for url in urls:
        try:
            f = feedparser.parse(url)
            for e in f.entries[:60]:
                title, link, lower = e.title, e.link, e.title.lower()
                # Zeitstempel extrahieren
                published = e.get('published', datetime.datetime.now().strftime('%d.%m. %H:%M'))
                
                impact_level = "low"
                if any(k in lower for k in high_impact_list): impact_level = "high"
                
                is_future = any(k in lower for k in future_words)
                score = 1 if any(k in lower for k in ["beat", "above", "hike", "bullish"]) else -1 if any(k in lower for k in ["miss", "below", "cut", "bearish"]) else 0
                
                # NUR NEWS MIT REALEM IMPACT (High Impact oder signifikantes Sentiment)
                if impact_level == "high" or abs(score) > 0:
                    events.append({"title": title, "link": link, "impact": impact_level, "score": score, "is_future": is_future, "raw": lower, "date": published})
        except: continue
    return events

# 5. ANALYSE LOGIK
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
            if e["is_future"] and (future_warning is None or e["impact"] == "high"):
                future_warning = e
            relevant_news.append(e)
            
    decision, color = ("KAUFEN", "#00ff00") if score >= 1 else ("VERKAUFEN", "#ff4b4b") if score <= -1 else ("NEUTRAL", "#b2b5be")
    return decision, color, relevant_news, future_warning

# 6. IP FÜR HANDY
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(("8.8.8.8", 80))
    network_url = f"http://{s.getsockname()[0]}:8501"; s.close()
except: network_url = "http://localhost:8501"

# 7. LAYOUT
st.title("💹 Trading ATM Impact Master")
st.caption(f"Fokus auf marktbewegende News | Stand: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}")

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
        p = name.replace(' (Gold)', '').split('/')
        b_url, q_url = get_icon_url(p[0]), get_icon_url(p[1] if len(p)>1 else "USD")
        if "XAU" in name: b_url = get_icon_url("XAU")
        if "BTC" in name: b_url = get_icon_url("BTC")
        if "US30" in name: b_url = get_icon_url("US30")
        
        with cols[j]:
            st.markdown(f'<div class="icon-container"><div class="icon-1" style="background-image: url(\'{b_url}\');"></div><div class="icon-2" style="background-image: url(\'{q_url}\');"></div></div><div class="pair-name">{name}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="signal-box" style="background-color: {color};">{decision}</div>', unsafe_allow_html=True)
            
            if future_alert:
                st.markdown(f'<div class="future-warning"><div class="warning-header">⚠️ VORSCHAU/MORGEN:</div>{future_alert["title"]}</div>', unsafe_allow_html=True)
                st.download_button("📅 Termin", create_ics(name, future_alert["title"]), f"{name}.ics", "text/calendar", key=f"b_{i}_{j}")

            with st.expander(f"Impact News ({len(news)})"):
                if news:
                    news.sort(key=lambda x: (x["impact"] == "high"), reverse=True)
                    news_html = "<div class='news-scroll-container'>"
                    for n in news:
                        icon = "🔮" if n["is_future"] else "🔥"
                        news_html += f"<div class='ff-high'>{icon} <a href='{n['link']}' target='_blank'>{n['title']}</a><span class='news-date'>{n['date']}</span></div>"
                    news_html += "</div>"
                    st.markdown(news_html, unsafe_allow_html=True)
                else: st.caption("Keine Impact News.")

st.divider()
components.html('<div class="tradingview-widget-container"><script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-events.js" async>{ "colorTheme": "dark", "isTransparent": false, "width": "100%", "height": "600", "locale": "de_DE", "importanceFilter": "-1,0,1" }</script></div>', height=600)

with st.sidebar:
    st.image(f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={network_url}")
    st.write(f"Handy-URL: `{network_url}`")
time.sleep(300); st.rerun()
