import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import os
import time

# 1. Page Configuration
st.set_page_config(page_title="Groww Pro Terminal", layout="wide")
st.title("🟢 My Trading Terminal (Groww Style)")

# --- V37: STABLE DATA ENGINE ---
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

# 2. Sidebar Settings (Groww Sidebar Style)
st.sidebar.header("🔍 Search Market")
selected_stock = st.sidebar.selectbox(f"Select from {len(stock_names)} stocks", stock_names, index=0)
ticker_symbol = stock_dict[selected_stock]

col1, col2 = st.sidebar.columns(2)
with col1:
    time_period = st.selectbox("Timeline", ["1d", "5d", "1mo", "1y"], index=0)
with col2:
    time_interval = st.selectbox("Candle", ["1m", "5m", "15m", "1h"], index=1)

st.sidebar.markdown("---")
st.sidebar.header("📊 Technicals")
show_indicators = st.sidebar.checkbox("Show EMA & VWAP", value=True)
show_rsi = st.sidebar.checkbox("Show RSI", value=True)

st.sidebar.markdown("---")
live_mode = st.sidebar.toggle("🟢 Live Auto-Refresh (30s)", value=False)

# 3. Calculation Engine
def apply_groww_technicals(df):
    if df is None or df.empty: return None
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    
    # EMAs & VWAP
    df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
    v = df['Volume'].values
    p = (df['High'] + df['Low'] + df['Close']).values / 3
    df['VWAP'] = (p * v).cumsum() / (v.cumsum() + 1e-10)
    
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-10))))
    return df

# 4. Main Display Logic
data = yf.download(ticker_symbol, period=time_period, interval=time_interval, progress=False)

if not data.empty:
    df = apply_groww_technicals(data)
    ltp = df['Close'].iloc[-1]
    prev = df['Close'].iloc[-2]
    change = ltp - prev
    pct = (change / prev) * 100
    
    # --- GROWW STYLE HEADER ---
    st.markdown(f"### {selected_stock}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("LTP", f"₹{ltp:.2f}", f"{change:.2f} ({pct:.2f}%)")
    c2.metric("Today's High", f"₹{df['High'].max():.2f}")
    c3.metric("Today's Low", f"₹{df['Low'].min():.2f}")
    c4.metric("Avg Vol", f"{int(df['Volume'].mean()):,}")

    # --- GROWW STYLE CHART ---
    rows = 2 if show_rsi else 1
    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.8, 0.2] if show_rsi else [1])

    # Groww Official Palette
    groww_green = '#00D09C'
    groww_red = '#EB5B3C'
    bg_color = '#FFFFFF' if not st.get_option("theme.base") == "dark" else '#121212'

    # 1. THE CANDLES
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        increasing_line_color=groww_green, decreasing_line_color=groww_red,
        increasing_fillcolor=groww_green, decreasing_fillcolor=groww_red,
        name='Price'
    ), row=1, col=1)

    if show_indicators:
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA9'], line=dict(color='#2196F3', width=1.2), name='EMA 9'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], line=dict(color='#FF9800', width=1.5, dash='dot'), name='VWAP'), row=1, col=1)

    if show_rsi:
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#7E57C2', width=2), name='RSI'), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color=groww_red, row=2, col=1, opacity=0.3)
        fig.add_hline(y=30, line_dash="dash", line_color=groww_green, row=2, col=1, opacity=0.3)

    # --- GROWW CHART LAYOUT ---
    fig.update_layout(
        height=750,
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        showlegend=False,
        margin=dict(l=10, r=60, t=10, b=10),
        uirevision=ticker_symbol,
        dragmode='pan'
    )

    fig.update_xaxes(showgrid=True, gridwidth=0.5, gridcolor='#2A2A2A', 
                     rangebreaks=[dict(bounds=["sat", "mon"]), dict(bounds=[15.5, 9.25], pattern="hour")])
    fig.update_yaxes(showgrid=True, gridwidth=0.5, gridcolor='#2A2A2A', side='right')

    # AI Suggestion in Sidebar
    with st.sidebar:
        st.markdown("---")
        st.header("🤖 AI Signal")
        if ltp > df['EMA9'].iloc[-1]:
            st.success("### 🟢 BUY\nTrend is Bullish")
        else:
            st.error("### 🔴 SELL\nTrend is Bearish")

    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': False})

    if live_mode:
        time.sleep(30)
        st.rerun()
else:
    st.error("Select a stock to view.")
