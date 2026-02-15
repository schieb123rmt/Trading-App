import streamlit as st
import feedparser
from textblob import TextBlob
import datetime
import time
import yfinance as yf
import pandas as pd
import streamlit.components.v1 as components

# 1. Konfiguration
st.set_page_config(page_title="Trading ATM Professional", layout="wide")

# CSS Styling
st.markdown("""
<style>
    div[data-testid="column"] { background-color: #1e1e1e; border-radius: 12px; padding: 15px; border: 1px solid #333; margin-bottom: 20px; }
    .icon-container { position: relative; width: 80px; height: 60px; margin: 0 auto 10px; }
    .icon-1 { width: 45px; height: 45px; border-radius: 50%; position: absolute; left: 0; top: 0; background-size: cover; z-index: 2; border: 2px solid #1e1e1e; }
    .icon-2 { width: 45px; height: 45px; border-radius: 50%; position: absolute; left: 28px; top: 12px; background-size: cover; z-index: 1; border: 2px solid #1e1e1e; }
    .pair-title { font-size: 1.1em; font-weight: bold; color: white; text-align: center; margin-bottom: 5px; }
    .signal-badge { padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.9em; }
    .tech-info { font-size: 0.75em; color: #aaa; margin-top: 5px; }
    .last-update { font-size: 0.8em; color: #555; text-align: center; margin-top: 30px; }
</style>
""", unsafe_allow_html=True)

# Hilfsfunktionen
def get_icon_url(c):
    crypto = {"BTC": "https://cryptologos.cc/logos/bitcoin-btc-logo.png", "ADA": "https://cryptologos.cc/logos/cardano-ada-logo.png", "XAU": "https://cdn-icons-png.flaticon.com/512/272/272530.png"}
    if c.upper() in crypto: return crypto[c.upper()]
    m = {"USD":"us","JPY":"jp","EUR":"eu","GBP":"gb","CHF":"ch","CAD":"ca","AUD":"au","US30":"us"}
    return f"https://flagcdn.com/w160/{m.get(c.upper(), 'un')}.png"

# --- TECHNISCHE ANALYSE (RSI + SMA) ---
def get_technical_data(ticker_symbol):
    try:
        # Wir holen die Daten der letzten 3 Monate
        df = yf.download(ticker_symbol, period="3mo", interval="1d", progress=False)
        
        if len(df) < 50: return 0, 0, 0 # Nicht genug Daten
        
        # 1. Aktueller Preis
        current_price = df['Close'].iloc[-1]
        if isinstance(current_price, pd.Series): current_price = current_price.iloc[0] # Fix für manche Pandas Versionen

        # 2. SMA 50 (Durchschnitt der letzten 50 Tage)
        sma_50 = df['Close'].rolling(window=50).mean().iloc[-1]
        if isinstance(sma_50, pd.Series): sma_50 = sma_50.iloc[0]

        # 3. RSI 14 (Relative Strength Index)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        if isinstance(rsi, pd.Series): rsi = rsi.iloc[0]
        
        return round(float(current_price), 4), round(float(sma_50), 4), round(float(rsi), 2)
    except Exception as e:
        return 0, 0, 0

# --- NEWS ANALYSE (Sentiment) ---
def get_news_sentiment(name):
    urls = ["https://www.fxstreet.com/rss/news", "https://www.dailyfx.com/feeds/forex-market-news"]
    search = name.split('/')[0].lower()
    if "XAU" in name: search = "gold"
    score, count = 0, 0
    headlines = []
    
    for url in urls:
        try:
            f = feedparser.parse(url)
            for e in f.entries[:10]:
                if search in e.title.lower():
                    val = TextBlob(e.title).sentiment.polarity
                    score += val
                    count += 1
                    headlines.append(e.title)
        except: continue
        
    avg = score / count if count > 0 else 0
    return avg, headlines

# --- HAUPT LOGIK: KOMBINATION ---
def analyze_market_pro(name, ticker):
    # 1. Hole Technische Daten (Fakten)
    price, sma, rsi = get_technical_data(ticker)
    
    # 2. Hole News Daten (Meinung)
    sentiment_score, news_list = get_news_sentiment(name)
    
    # --- PROGNOSE BERECHNUNG ---
    signal_score = 0 # Start bei 0 (Neutral)
    reasons = []

    # A. Bewertung RSI (Momentum)
    if rsi > 70: 
        signal_score -= 2 # Überkauft -> Verkaufssignal
        reasons.append(f"⚠️ RSI sehr hoch ({rsi}) - Überkauft")
    elif rsi < 30: 
        signal_score += 2 # Überverkauft -> Kaufsignal
        reasons.append(f"✅ RSI sehr tief ({rsi}) - Überverkauft")
    else:
        reasons.append(f"ℹ️ RSI neutral ({rsi})")

    # B. Bewertung SMA (Trend)
    if price > sma:
        signal_score += 1 # Über dem Durchschnitt -> Bullish
        reasons.append("✅ Preis über 50-Tage Trend")
    else:
        signal_score -= 1 # Unter dem Durchschnitt -> Bearish
        reasons.append("🔻 Preis unter 50-Tage Trend")
        
    # C. Bewertung News (Sentiment)
    if sentiment_score > 0.1:
        signal_score += 1
        reasons.append("✅ Nachrichten positiv")
    elif sentiment_score < -0.1:
        signal_score -= 1
        reasons.append("🔻 Nachrichten negativ")
    else:
        reasons.append("ℹ️ Nachrichten neutral")
        
    # Ergebnis-Text
    final_decision = "NEUTRAL"
    color = "#ffa500" # Orange
    
    if signal_score >= 2:
        final_decision = "STRONG BUY"
        color = "#00ff00" # Grün
    elif signal_score == 1:
        final_decision = "BUY"
        color = "#90ee90" # Hellgrün
    elif signal_score <= -2:
        final_decision = "STRONG SELL"
        color = "#ff0000" # Rot
    elif signal_score == -1:
        final_decision = "SELL"
        color = "#ff6b6b" # Hellrot
        
    return final_decision, color, reasons, news_list, price

# --- LAYOUT ---
st.title("💹 Trading ATM Professional (News + Tech)")

pairs = [
    ("USD/JPY", "USDJPY=X"), ("EUR/USD", "EURUSD=X"), ("GBP/USD", "GBPUSD=X"), 
    ("XAU/USD", "GC=F"), ("BTC/USD", "BTC-USD"), ("US30", "^DJI")
]

st.info("Diese App kombiniert jetzt technische Indikatoren (RSI, SMA) mit News-Daten.")

for i in range(0, len(pairs), 3):
    cols = st.columns(3)
    for j, (name, ticker) in enumerate(pairs[i:i+3]):
        
        # Hier dauert es etwas länger, weil yfinance Daten lädt
        with st.spinner(f"Analysiere {name}..."):
            decision, color, reasons, news, price = analyze_market_pro(name, ticker)
        
        parts = name.replace(' (Gold)', '').split('/')
        
        with cols[j]:
            st.markdown(f"""
                <div class="icon-container">
                    <div class="icon-1" style="background-image: url('{get_icon_url(parts[0])}');"></div>
                    <div class="icon-2" style="background-image: url('{get_icon_url(parts[1] if len(parts)>1 else 'USD')}');"></div>
                </div>
                <div class="pair-title">{name}</div>
                <div style="text-align:center; font-size: 1.2em; font-weight:bold; margin-bottom:5px;">
                    Kurs: {price}
                </div>
                <div style="text-align:center; background-color:{color}; color:black; padding:5px; border-radius:5px; font-weight:bold;">
                    {decision}
                </div>
                <div class="tech-info">
                    {"<br>".join(reasons)}
                </div>
            """, unsafe_allow_html=True)
            
            with st.expander("News Quellen"):
                if news:
                    for n in news[:3]: st.write(f"- {n}")
                else: st.write("Keine News.")

st.markdown(f"<div class='last-update'>Update: {datetime.datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)

if st.button("Aktualisieren"):
    st.rerun()
