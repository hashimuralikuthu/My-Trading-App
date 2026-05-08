import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import os
import time

# 1. Page Configuration
st.set_page_config(page_title="Candle Master Terminal", layout="wide")
st.title("💎 Pro Trading Terminal V36 (The Candle Master)")

# --- V36: DATA ENGINE ---
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
st.sidebar.header("🛠️ Advanced Indicators")
show_pivots = st.sidebar.checkbox("Pivot Points (R1/S1)", value=True)
show_vwap = st.sidebar.checkbox("VWAP (Anchor)", value=True)
show_rsi = st.sidebar.checkbox("RSI (Strength)", value=True)

st.sidebar.markdown("---")
live_mode = st.sidebar.toggle("🟢 Enable Live Auto-Update", value=False)

# 3. Indicator Calculation
def apply_indicators(df):
    if df is None or df.empty: return None
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    
    # 1. VWAP
    v = df['Volume'].values
    p = (df['High'] + df['Low'] + df['Close']).values / 3
    df['VWAP'] = (p * v).cumsum() / (v.cumsum() + 1e-10)
    
    # 2. Pivots
    high = df['High'].max()
    low = df['Low'].min()
    close = df['Close'].iloc[-1]
    df['PP'] = (high + low + close) / 3
    df['R1'] = (2 * df['PP']) - low
    df['S1'] = (2 * df['PP']) - high
    
    # 3. RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-10))))
    return df

# 4. Display Logic
data = yf.download(ticker_symbol, period=time_period, interval=time_interval, progress=False)

if not data.empty:
    df = apply_indicators(data)
    ltp = df['Close'].iloc[-1]
    change = ltp - df['Close'].iloc[-2]
    pct = (change / df['Close'].iloc[-2]) * 100
    
    # Top Row Metrics
    st.subheader(f"📊 {selected_stock}")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("LTP (Price)", f"₹{ltp:.2f}", f"{change:.2f} ({pct:.2f}%)")
    m2.metric("Day High", f"₹{df['High'].max():.2f}")
    m3.metric("Day Low", f"₹{df['Low'].min():.2f}")
    m4.metric("Pivot (PP)", f"₹{df['PP'].iloc[-1]:.2f}")

    # --- THE MASTER CANDLESTICK GRAPH ---
    rows = 2 if show_rsi else 1
    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.8, 0.2] if show_rsi else [1])

    # 🟢 Neon Green & 🔴 Bright Red
    up_c = '#00FF00' 
    down_c = '#FF0000'

    # 1. The Candlesticks (The "Must-Have")
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name='Candles', 
        increasing_fillcolor=up_c, increasing_line_color=up_c,
        decreasing_fillcolor=down_c, decreasing_line_color=down_c,
        line=dict(width=1.5) # Thicker wicks
    ), row=1, col=1)

    if show_vwap:
        fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], line=dict(color='orange', width=2), name='VWAP'), row=1, col=1)
    
    if show_pivots:
        fig.add_trace(go.Scatter(x=df.index, y=df['R1'], line=dict(color='lightgreen', dash='dot'), name='R1'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['S1'], line=dict(color='lightpink', dash='dot'), name='S1'), row=1, col=1)

    if show_rsi:
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#b388ff', width=2), name='RSI'), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1, opacity=0.3)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1, opacity=0.3)

    # Calculate default zoom (Last 50 candles)
    last_idx = len(df)
    start_idx = max(0, last_idx - 50)
    
    fig.update_layout(
        height=800, template="plotly_dark", xaxis_rangeslider_visible=False,
        margin=dict(l=10, r=60, t=10, b=10), 
        plot_bgcolor='#000000', paper_bgcolor='#000000', # Deep black for max contrast
        uirevision=ticker_symbol, dragmode='pan',
        xaxis=dict(range=[df.index[start_idx], df.index[-1]]) # Focus on latest candles
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=0.5, gridcolor='#2a2e39', 
                     rangebreaks=[dict(bounds=["sat", "mon"]), dict(bounds=[15.5, 9.25], pattern="hour")])
    fig.update_yaxes(showgrid=True, gridwidth=0.5, gridcolor='#2a2e39', side='right')

    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': False})

    if live_mode:
        time.sleep(30)
        st.rerun()
else:
    st.error("Select a stock to see the Master Candles.")
