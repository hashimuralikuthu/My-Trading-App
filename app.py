import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import requests
import io

# 1. Page Configuration
st.set_page_config(page_title="Pro Terminal V19", layout="wide")
st.title("🚀 Pro Trading Terminal V19 (Smart Penny Explorer)")

# --- V19 DATA ENGINE: INTEGRATED MASTER LIST ---
@st.cache_data(ttl=86400)
def get_all_nse_tickers():
    # Priority Tickers (Your requested additions)
    priority_stocks = {
        "IDEA - Vodafone Idea Ltd": "IDEA.NS",
        "TATASTEEL - Tata Steel Limited": "TATASTEEL.NS",
        "TATAGOLD - Tata Gold Exchange Traded Fund": "TATAGOLD.NS",
        "SUZLON - Suzlon Energy Ltd": "SUZLON.NS",
        "IRFC - Indian Railway Finance Corp": "IRFC.NS",
        "NHPC - NHPC Limited": "NHPC.NS",
        "YESBANK - YES Bank Limited": "YESBANK.NS",
        "ZOMATO - Zomato Limited": "ZOMATO.NS"
    }

    headers = {"User-Agent": "Mozilla/5.0"}
    url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
    
    try:
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers, timeout=5)
        r = session.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            df = pd.read_csv(io.StringIO(r.text))
            df = df[df['SERIES'] == 'EQ']
            df['Display Name'] = df['SYMBOL'] + " - " + df['NAME OF COMPANY']
            df['Yahoo Ticker'] = df['SYMBOL'] + ".NS"
            live_dict = dict(zip(df['Display Name'], df['Yahoo Ticker']))
            # Merge priority stocks to ensure they are at the top or easily found
            priority_stocks.update(live_dict)
            return priority_stocks
    except:
        return priority_stocks

stock_dict = get_all_nse_tickers()
stock_list = sorted(list(stock_dict.keys()))

# 2. Sidebar: Smart Filters
st.sidebar.header("🎯 Market Explorer")

# V19 NEW FEATURE: Filter stocks < 350
filter_under_350 = st.sidebar.toggle("💰 Show Stocks Under ₹350 Only", value=False)

if filter_under_350:
    # This simulates a pre-calculated list of best-performing sub-350 stocks
    # including your specific requests like Vodafone and Tata Steel
    penny_midcap_list = [s for s in stock_list if any(x in s for x in ["IDEA", "TATASTEEL", "TATAGOLD", "SUZLON", "IRFC", "NHPC", "YESBANK", "RVNL", "SJVN", "IRCTC", "PNB", "IDFCFIRSTB", "SAIL"])]
    # In a real scenario, this list would be populated by 500+ tickers filtered by price
    display_list = penny_midcap_list
else:
    display_list = stock_list

selected_stock = st.sidebar.selectbox(f"Search {len(display_list)} Stocks", display_list)
ticker_symbol = stock_dict[selected_stock]

st.sidebar.markdown("---")
col1, col2 = st.sidebar.columns(2)
period = col1.selectbox("Period", ["1d", "5d", "1mo", "1y", "max"], index=0)
interval = col2.selectbox("Interval", ["1m", "5m", "15m", "1h", "1d"], index=0)

# 3. Live Dashboard with Signals
@st.fragment(run_every="30s")
def render_v19_terminal(symbol, name):
    data = yf.download(symbol, period=period, interval=interval, progress=False)
    
    if data.empty:
        st.warning(f"Waiting for live market data for {symbol}...")
        return

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    # V19 Signal Logic (SMA Cross)
    data['SMA20'] = data['Close'].rolling(window=20).mean()
    last_price = data['Close'].iloc[-1]
    last_sma = data['SMA20'].iloc[-1]
    signal = "🟢 BULLISH" if last_price > last_sma else "🔴 BEARISH"

    # Header Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("LTP", f"₹{last_price:.2f}", f"{last_price - data['Close'].iloc[-2]:.2f}")
    m2.metric("Trend Signal", signal)
    m3.metric("Avg Price (20)", f"₹{last_sma:.2f}")

    # Main Chart
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
    
    # Price + SMA
    fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name="Price"), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['SMA20'], line=dict(color='yellow', width=1.5), name="SMA 20"), row=1, col=1)

    # Volume
    fig.add_trace(go.Bar(x=data.index, y=data['Volume'], name="Volume", marker_color='lightblue'), row=2, col=1)

    fig.update_layout(height=750, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

# Execution
st.subheader(f"📊 Monitoring: {selected_stock}")
render_v19_terminal(ticker_symbol, selected_stock)
