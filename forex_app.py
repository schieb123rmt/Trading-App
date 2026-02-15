import streamlit as st
import feedparser
from textblob import TextBlob
import datetime
import time
import streamlit.components.v1 as components

# 1. Seiten-Konfiguration
st.set_page_config(page_title="Calendar Forecast Scanner", layout="wide")

# CSS für klare Signale
st.markdown("""
<style>
    div[data-testid="column"] {
        background-color: #1e1e1e;
        border-radius: 10px;
        padding: 15px;
        border: 1px solid #333;
        margin-bottom: 20px;
    }
    .main-signal { font-size: 1.8em; font-weight: 900; text-align: center; margin: 10px 0; }
    .sub-text { color: #aaa; font-size: 0.8em; text-align: center; }
    .reason-box { background-color: #2b2b2b; padding: 10px; border-radius: 5px; font-size: 0.85em; margin-top: 10px; }
    .highlight-green { color: #4caf50; font-weight: bold; }
    .highlight-red { color: #f44336; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Icons
def get_icon(c):
    return f"https://flagcdn.com/w160/{c.lower()[:2]}.png" if c not in ["BTC","ADA","XAU","US30"] else "https://cdn-icons-png.flaticon.com/512/272/272530.png"

# --- DIE LOGIK: PROGNOSE VS REALITÄT ---
def analyze_forecast_reaction(name):
    # Wir nutzen Investing.com und FXStreet, da diese SOFORT nach den Zahlen berichten
    urls = [
        "https://www.investing.com/rss/news_25.rss", # Speziell für Wirtschaftskalender News
        "https://www.fxstreet.com/rss/news"
    ]
    
    search_term = name.split('/')[0].lower()
    if "US30" in name: search_term = "dow"
    if "XAU" in name: search_term = "gold"
    
    score = 0
    found_reasons = []
    
    # 1. WÖRTERBUCH: Was bedeutet "Besser als Prognose"?
    # Diese Wörter deuten darauf hin, dass die Prognose geschlagen wurde -> Währung steigt
    bullish_signals = [
        "beat estimate", "beats forecast", "above expectation", "stronger than expected", 
        "better than expected", "surprise jump", "hike", "optimistic"
    ]
    
    # Diese Wörter deuten darauf hin, dass die Prognose verfehlt wurde -> Währung fällt
    bearish_signals = [
        "missed estimate", "misses forecast", "below expectation", "weaker than expected", 
        "worse than expected", "surprise drop", "cut", "pessimistic"
    ]

    for url in urls:
        try:
            f = feedparser.parse(url)
            for e in f.entries[:15]:
                title_lower = e.title.lower()
                
                # Ist die News relevant?
                if search_term in title_lower or "market" in title_lower:
                    
                    # Suche nach Bullish Signalen (Prognose übertroffen)
                    for word in bullish_signals:
                        if word in title_lower:
                            score += 1
                            # Formatierung für die Anzeige
                            clean_title = e.title.replace(word, f"<b>{word.upper()}</b>") 
                            found_reasons.append(f"🟢 {clean_title}")
                            
                    # Suche nach Bearish Signalen (Prognose verfehlt)
                    for word in bearish_signals:
                        if word in title_lower:
                            score -= 1
                            clean_title = e.title.replace(word, f"<b>{word.upper()}</b>")
                            found_reasons.append(f"🔴 {clean_title}")
        except: continue
    
    # Auswertung
    if score > 0: return "STEIGEN", "#00ff00", found_reasons
    if score < 0: return "FALLEN", "#ff4b4b", found_reasons
    return "NEUTRAL", "#ffa500", ["Keine Abweichung von Prognose in den News."]

# --- LAYOUT ---
st.title("📊 Trading ATM: Prognose Scanner")
st.markdown("Dieses Tool scannt News nach **'Forecast vs. Actual'** Ereignissen. Wenn eine Zahl besser ist als erwartet, signalisiert es STEIGEN.")

pairs = [("EUR/USD", "eu"), ("USD/JPY", "us"), ("GBP/USD", "gb"), ("XAU/USD", "gold"), ("US30", "us")]

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Live Analyse der Wirtschaftszahlen")
    for pair, country in pairs:
        signal, color, reasons = analyze_forecast_reaction(pair)
        
        with st.container():
            # Die Box für jedes Paar
            c1, c2 = st.columns([1, 4])
            with c1:
                st.image(get_icon(country), width=50)
                st.markdown(f"**{pair}**")
            with c2:
                # Das dicke Signal
                st.markdown(f"<div class='main-signal' style='color: {color};'>{signal}</div>", unsafe_allow_html=True)
                
                # Die Gründe (Expander)
                with st.expander("Warum? (Gefundene Prognosen)"):
                    if reasons and "Keine" not in reasons[0]:
                        for r in reasons:
                            st.markdown(r, unsafe_allow_html=True) # HTML erlaubt Fettdruck
                    else:
                        st.caption("Aktuell keine 'Überraschungen' im Wirtschaftskalender gefunden.")

with col2:
    st.subheader("Der echte Kalender (Zur Kontrolle)")
    # Hier betten wir den TradingView Kalender ein, damit du die echten Zahlen siehst
    components.html("""
    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-events.js" async>
      {
      "colorTheme": "dark",
      "isTransparent": false,
      "width": "100%",
      "height": "600",
      "locale": "de_DE",
      "importanceFilter": "-1,0,1"
    }
      </script>
    </div>
    """, height=600)

st.markdown("---")
if st.button("Jetzt Scannen"):
    st.rerun()
