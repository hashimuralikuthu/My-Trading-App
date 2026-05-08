import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import os
import time

# 1. Page Configuration
st.set_page_config(page_title="Pro Trading Terminal", layout="wide")
st.title("🔴 My Pro Trading Terminal V27 (Live AI Sync)")

# --- V27: DATA ENGINE ---
@st.cache_data
def get_local_stock_list():
    file_path = 'EQUITY_L.csv'
    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path)
            df.columns = df.columns.str.strip() 
            df = df[df['SERIES'].str.strip() == 'EQ'].copy()
            df['Display Name'] = df['SYMBOL'] + " - " + df['NAME OF COMPANY']
            df['Yahoo Ticker'] = df['SYMBOL'].astype(str) + ".NS"
            return dict(zip(df['Display Name'], df['Yahoo Ticker']))
        except:
            return {"RELIANCE - Reliance Industries": "RELIANCE.NS"}
    else:
        return {"RELIANCE - Reliance Industries": "RELIANCE.NS"}

stock_dict = get_local_stock_list()
stock_display_names = sorted(list(stock_dict.keys()))

# 2. Sidebar Settings
st.sidebar.header("🎯 Market Explorer")
selected_display_name = st.sidebar.selectbox(f"Search {len(stock_display_names)} Stocks", stock_display_names, index=0)
ticker_symbol = stock_dict[selected_display_name]

col1, col2 = st.sidebar.columns(2)
with col1:
    time_period = st.selectbox("Period", ["1d", "5d", "1mo", "1y"], index=0)
with col2:
    time_interval = st.selectbox("Candle", ["1m", "5m", "15m", "1h", "1d"], index=1)

st.sidebar.markdown("---")
st.sidebar.header("⚡ Live Engine")
# THE TOGGLE IS BACK
live_mode = st.sidebar.toggle("🟢 Enable Live Auto-Update", value=False)

# 3. Indicator Logic
def get_data(symbol, period, interval):
    data = yf.download(tickers=symbol, period=period, interval=interval, progress=False)
    if data.empty: return None
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    
    # Technicals
    data['SMA20'] = data['Close'].rolling(window=20).mean()
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / (loss + 1e-10)
    data['RSI'] = 100 - (100 / (1 + rs))
    return data

# 4. Display Logic
df = get_data(ticker_symbol, time_period, time_interval)

if df is not None:
    last_price = float(df['Close'].iloc[-1])
    current_rsi = float(df['RSI'].iloc[-1])
    current_sma = float(df['SMA20'].iloc[-1])
    
    # --- AI SUGGESTION SIDE SCREEN ---
    with st.sidebar:
        st.markdown("---")
        st.header("🤖 AI Suggestion")
        if current_rsi > 70:
            st.error("### 🔴 SELL\n**RSI Overbought:** Market is too high, wait for a drop.")
        elif current_rsi < 30:
            st.success("### 🟢 BUY\n**RSI Oversold:** Good time to enter, bounce expected.")
        elif last_price > current_sma:
            st.success("### 🟢 BUY\n**Trend:** Price is strong above 20-day Average.")
        else:
            st.warning("### 🔴 SELL\n**Trend:** Price is weak below 20-day Average.")
        
        if live_mode:
            st.info("🔄 Auto-refreshing every 30 seconds...")

    # Main Dashboard
    st.subheader(f"📊 {selected_display_name}")
    m1, m2, m3 = st.columns(3)
    m1.metric("LTP", f"₹{last_price:.2f}")
    m2.metric("Day High", f"₹{df['High'].max():.2f}")
    m3.metric("RSI (14)", f"{current_rsi:.1f}")

    # Chart
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA20'], line=dict(color='yellow', width=1.5), name='SMA 20'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='magenta', width=1.5), name='RSI'), row=2, col=1)
    
    fig.update_layout(height=700, template="plotly_dark", xaxis_rangeslider_visible=False, dragmode='pan', uirevision=ticker_symbol)
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

    # --- THE LIVE REFRESH TIMER ---
    if live_mode:
        time.sleep(30)
        st.rerun()
else:
    st.error("Data error. Try a different stock or period.")
