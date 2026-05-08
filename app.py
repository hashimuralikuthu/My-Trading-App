import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import requests
import io
import time  # NEW: We need this to control the live timer

# 1. Page Configuration
st.set_page_config(page_title="Pro Trading Terminal", layout="wide")
st.title("🔴 My Pro Trading Terminal V10 (LIVE)")

# --- Robust NSE Ticker Fetching ---
@st.cache_data(ttl=86400)
def get_all_nse_tickers():
    try:
        url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=15)
        df = pd.read_csv(io.StringIO(r.text))
        df = df[df['SERIES'] == 'EQ']
        tickers = sorted((df['SYMBOL'].astype(str) + ".NS").tolist())
        return tickers
    except Exception as e:
        return ["RELIANCE.NS", "TCS.NS", "ZOMATO.NS", "HDFCBANK.NS", "INFY.NS", "TATAMOTORS.NS"]

all_stocks = get_all_nse_tickers()

# 2. Sidebar Settings
st.sidebar.header("🎯 Market Explorer")
ticker_symbol = st.sidebar.selectbox("Search Stock Name (Type here)", all_stocks, index=all_stocks.index("ZOMATO.NS") if "ZOMATO.NS" in all_stocks else 0)

col1, col2 = st.sidebar.columns(2)
with col1:
    time_period = st.selectbox("Period", ["1d", "5d", "1mo", "3mo"], index=0)
with col2:
    time_interval = st.selectbox("Candle", ["1m", "5m", "15m", "30m"], index=0)

st.sidebar.markdown("---")
st.sidebar.header("🛠️ Technical Tools")
show_sma = st.sidebar.checkbox("20 SMA (Trend)", value=True)
show_ema = st.sidebar.checkbox("50 EMA (Support)", value=False)
show_rsi = st.sidebar.checkbox("RSI (Overbought)", value=False)

st.sidebar.markdown("---")
# NEW: LIVE MODE TOGGLE
st.sidebar.header("⚡ Live Engine")
live_mode = st.sidebar.toggle("🟢 Enable Live Auto-Update", value=False)
if live_mode:
    st.sidebar.success("Live Mode Active: Updating every 30s")

# 3. Data Fetching Logic
# NEW: We changed ttl to 30 seconds so it forces a fresh download!
@st.cache_data(ttl=30)
def load_data(ticker, period, interval):
    try:
        data = yf.download(tickers=ticker, period=period, interval=interval, progress=False)
        if data.empty: return pd.DataFrame()
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        return data
    except:
        return pd.DataFrame()

data = load_data(ticker_symbol, time_period, time_interval)

# 4. Dashboard Visuals
if not data.empty:
    last_price = data['Close'].iloc[-1]
    prev_price = data['Close'].iloc[-2]
    change = last_price - prev_price
    pct_change = (change / prev_price) * 100

    c1, c2, c3 = st.columns(3)
    c1.metric("Current Price", f"₹{last_price:.2f}", f"{change:.2f} ({pct_change:.2f}%)")
    c2.metric("Day High", f"₹{data['High'].max():.2f}")
    c3.metric("Day Low", f"₹{data['Low'].min():.2f}")

    data['SMA20'] = data['Close'].rolling(window=20).mean()
    data['EMA50'] = data['Close'].ewm(span=50, adjust=False).mean()
    
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data['RSI'] = 100 - (100 / (1 + rs))

    rows = 3 if show_rsi else 2
    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.05, 
                        row_width=[0.2, 0.2, 0.6] if show_rsi else [0.3, 0.7])

    bull_color = '#00C853' 
    bear_color = '#FF5252' 

    fig.add_trace(go.Candlestick(
        x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], 
        name='Price',
        increasing_line_color=bull_color, decreasing_line_color=bear_color,
        increasing_fillcolor=bull_color, decreasing_fillcolor=bear_color
    ), row=1, col=1)

    if show_sma:
        fig.add_trace(go.Scatter(x=data.index, y=data['SMA20'], line=dict(color='#FF8C00', width=1.5), name='SMA 20'), row=1, col=1)
    if show_ema:
        fig.add_trace(go.Scatter(x=data.index, y=data['EMA50'], line=dict(color='#2962FF', width=1.5), name='EMA 50'), row=1, col=1)

    colors = [bull_color if c >= o else bear_color for o, c in zip(data['Open'], data['Close'])]
    fig.add_trace(go.Bar(x=data.index, y=data['Volume'], marker_color=colors, name='Volume'), row=2, col=1)

    if show_rsi:
        fig.add_trace(go.Scatter(x=data.index, y=data['RSI'], line=dict(color='#AA00FF', width=2), name='RSI'), row=3, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color=bear_color, row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color=bull_color, row=3, col=1)

    fig.update_layout(
        height=850, 
        template="plotly_dark", 
        xaxis_rangeslider_visible=False, 
        showlegend=True,
        dragmode='pan',          
        hovermode='x unified',   
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    chart_config = {
        'scrollZoom': True,      
        'displayModeBar': True,  
        'modeBarButtonsToAdd': ['drawline', 'eraseshape'], 
        'displaylogo': False     
    }
    
    st.plotly_chart(fig, use_container_width=True, config=chart_config)

else:
    st.error(f"Error fetching data for {ticker_symbol}. Please try a different timeframe.")

# --- THE LIVE ENGINE ---
# If the user turns the switch on, wait 30 seconds and reload the page automatically
if live_mode:
    time.sleep(30)
    st.rerun()
