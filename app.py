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
st.title("🚀 Pro Trading Terminal V30 (Perfect Charts)")

# --- V30: DATA ENGINE ---
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
st.sidebar.header("🛠️ Chart Options")
show_vwap = st.sidebar.checkbox("VWAP (Intraday)", value=True)
show_macd = st.sidebar.checkbox("MACD", value=True)
show_rsi = st.sidebar.checkbox("RSI", value=True)

st.sidebar.markdown("---")
live_mode = st.sidebar.toggle("🟢 Enable Live Auto-Update", value=False)

# 3. Technical Calculation Engine
def apply_indicators(df):
    if df is None or df.empty: return None
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    
    # VWAP
    v = df['Volume'].values
    p = (df['High'] + df['Low'] + df['Close']).values / 3
    df['VWAP'] = (p * v).cumsum() / v.cumsum()
    
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-10))))
    
    # MACD
    df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['Hist'] = df['MACD'] - df['Signal']
    return df

# 4. Main Display Logic
data = yf.download(ticker_symbol, period=time_period, interval=time_interval, progress=False)

if not data.empty:
    df = apply_indicators(data)
    
    # Price Metrics
    ltp = df['Close'].iloc[-1]
    change = ltp - df['Close'].iloc[-2]
    pct = (change / df['Close'].iloc[-2]) * 100
    
    st.subheader(f"📊 {selected_stock}")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("LTP", f"₹{ltp:.2f}", f"{change:.2f} ({pct:.2f}%)")
    m2.metric("High", f"₹{df['High'].max():.2f}")
    m3.metric("Low", f"₹{df['Low'].min():.2f}")
    m4.metric("Vol", f"{df['Volume'].iloc[-1]:,}")

    # --- PERFECT CHART STYLING ---
    rows = 1
    if show_rsi: rows += 1
    if show_macd: rows += 1
    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.6] + [0.2]*(rows-1))

    # Professional Colors
    up_color = '#26a69a' # Emerald Green
    down_color = '#ef5350' # Rose Red

    # 1. THE PERFECT CANDLES
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name='Price',
        increasing_line_color=up_color, decreasing_line_color=down_color,
        increasing_fillcolor=up_color, decreasing_fillcolor=down_color,
    ), row=1, col=1)

    if show_vwap:
        fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], line=dict(color='#ff9800', width=1.5), name='VWAP'), row=1, col=1)

    # 2. RSI
    curr = 2
    if show_rsi:
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#9c27b0', width=2), name='RSI'), row=curr, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="#ef5350", row=curr, col=1, opacity=0.5)
        fig.add_hline(y=30, line_dash="dash", line_color="#26a69a", row=curr, col=1, opacity=0.5)
        curr += 1

    # 3. MACD
    if show_macd:
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], line=dict(color='#2196f3'), name='MACD'), row=curr, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['Signal'], line=dict(color='#ffeb3b'), name='Signal'), row=curr, col=1)
        # MACD Histogram with colors
        hist_colors = [up_color if v > 0 else down_color for v in df['Hist']]
        fig.add_trace(go.Bar(x=df.index, y=df['Hist'], marker_color=hist_colors, name='Hist'), row=curr, col=1)

    # LAYOUT IMPROVEMENTS (The "Perfect" Secret)
    fig.update_layout(
        height=850,
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        showlegend=False,
        margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor='#131722', # TradingView Dark Blue-Black
        paper_bgcolor='#131722',
        uirevision=ticker_symbol,
        dragmode='pan'
    )

    # Remove weekend gaps and clean grid
    fig.update_xaxes(
        showgrid=True, gridwidth=1, gridcolor='#2a2e39',
        rangebreaks=[dict(bounds=["sat", "mon"]), dict(bounds=[15.5, 9.25], pattern="hour")] # Hide weekends & night
    )
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#2a2e39', side='right')

    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

    if live_mode:
        time.sleep(30)
        st.rerun()
else:
    st.error("No data found for this period.")
