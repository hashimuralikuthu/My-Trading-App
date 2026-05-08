import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import os
import time

# 1. Page Configuration
st.set_page_config(page_title="Intraday Pro Terminal", layout="wide")
st.title("🚀 Intraday Pro Terminal V29 (Price + Indicators)")

# --- V29: DATA ENGINE ---
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
        except: return {"RELIANCE": "RELIANCE.NS"}
    return {"RELIANCE": "RELIANCE.NS"}

stock_dict = get_local_stock_list()
stock_names = sorted(list(stock_dict.keys()))

# 2. Sidebar Settings
st.sidebar.header("🎯 Market Explorer")
selected_stock = st.sidebar.selectbox(f"Search {len(stock_names)} Stocks", stock_names, index=0)
ticker_symbol = stock_dict[selected_stock]

col1, col2 = st.sidebar.columns(2)
with col1:
    time_period = st.selectbox("Period", ["1d", "5d", "1mo", "1y"], index=0)
with col2:
    time_interval = st.selectbox("Candle", ["1m", "5m", "15m", "30m", "1h", "1d"], index=1)

st.sidebar.markdown("---")
st.sidebar.header("🛠️ Intraday Indicators")
show_vwap = st.sidebar.checkbox("VWAP (Intraday Anchor)", value=True)
show_bb = st.sidebar.checkbox("Bollinger Bands", value=False)
show_macd = st.sidebar.checkbox("MACD (Momentum)", value=True)
show_rsi = st.sidebar.checkbox("RSI (Strength)", value=True)

st.sidebar.markdown("---")
live_mode = st.sidebar.toggle("🟢 Enable Live Auto-Update", value=False)

# 3. Technical Calculation Engine
def apply_indicators(df):
    if df is None or df.empty: return None
    # Correct columns for multi-index if needed
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    
    # 1. VWAP
    v = df['Volume'].values
    p = (df['High'] + df['Low'] + df['Close']).values / 3
    df['VWAP'] = (p * v).cumsum() / v.cumsum()
    
    # 2. Bollinger Bands
    df['SMA20'] = df['Close'].rolling(window=20).mean()
    df['stddev'] = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['SMA20'] + (df['stddev'] * 2)
    df['BB_Lower'] = df['SMA20'] - (df['stddev'] * 2)
    
    # 3. RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-10))))
    
    # 4. MACD
    df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['Signal_Line']
    return df

# 4. Main Display Logic
data = yf.download(ticker_symbol, period=time_period, interval=time_interval, progress=False)

if not data.empty:
    df = apply_indicators(data)
    
    # Calculations for Metrics
    ltp = df['Close'].iloc[-1]
    prev_close = df['Close'].iloc[-2]
    change = ltp - prev_close
    pct_change = (change / prev_close) * 100
    
    # --- AI Sideboard Suggestions ---
    with st.sidebar:
        st.markdown("---")
        st.header("🤖 AI Trade Signal")
        last = df.iloc[-1]
        if last['Close'] > last['VWAP'] and last['MACD'] > last['Signal_Line']:
            st.success("### 🟢 STRONG BUY\nPrice > VWAP + Bullish MACD.")
        elif last['Close'] < last['VWAP'] and last['MACD'] < last['Signal_Line']:
            st.error("### 🔴 STRONG SELL\nPrice < VWAP + Bearish MACD.")
        else:
            st.warning("### ⚪ HOLD / WAIT\nMixed signals. No clear trend.")

    # Main Screen Top Row
    st.subheader(f"📊 {selected_stock}")
    
    # 🌟 NEW PRICE METRICS ROW 🌟
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("LTP (Price)", f"₹{ltp:.2f}", f"{change:.2f} ({pct_change:.2f}%)")
    m2.metric("Day High", f"₹{df['High'].max():.2f}")
    m3.metric("Day Low", f"₹{df['Low'].min():.2f}")
    m4.metric("Volume", f"{df['Volume'].iloc[-1]:,}")

    # Chart Setup
    rows = 1
    if show_rsi: rows += 1
    if show_macd: rows += 1
    row_heights = [0.6] + [0.2] * (rows - 1)
    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=row_heights)

    # 1. Price Chart
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
    if show_vwap:
        fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], line=dict(color='orange', width=2), name='VWAP'), row=1, col=1)
    if show_bb:
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_Upper'], line=dict(color='rgba(173, 204, 255, 0.3)', width=1), name='BB Upper'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_Lower'], line=dict(color='rgba(173, 204, 255, 0.3)', width=1), name='BB Lower'), row=1, col=1)

    # 2. RSI
    curr_row = 2
    if show_rsi:
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='magenta', width=1.5), name='RSI'), row=curr_row, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=curr_row, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=curr_row, col=1)
        curr_row += 1

    # 3. MACD
    if show_macd:
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], line=dict(color='cyan'), name='MACD'), row=curr_row, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['Signal_Line'], line=dict(color='yellow'), name='Signal'), row=curr_row, col=1)
        colors = ['green' if val > 0 else 'red' for val in df['MACD_Hist']]
        fig.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], marker_color=colors, name='Hist'), row=curr_row, col=1)

    fig.update_layout(height=800, template="plotly_dark", xaxis_rangeslider_visible=False, uirevision=ticker_symbol, dragmode='pan', margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

    # Auto-refresh logic
    if live_mode:
        time.sleep(30)
        st.rerun()
else:
    st.error("Select a stock to see data.")
