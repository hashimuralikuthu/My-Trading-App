import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import os
import time

# 1. Page Configuration
st.set_page_config(page_title="Pro Terminal V34", layout="wide")
st.title("💎 Pro Trading Terminal V34 (Perfect Candles)")

# --- V34: DATA ENGINE ---
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
show_indicators = st.sidebar.toggle("Show EMAs & VWAP", value=True)
show_rsi = st.sidebar.toggle("Show RSI Strength", value=True)

st.sidebar.markdown("---")
live_mode = st.sidebar.toggle("🟢 Enable Live Auto-Update", value=False)

# 3. Technical Calculation Engine
def apply_indicators(df):
    if df is None or df.empty: return None
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    
    # Intraday EMAs
    df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
    
    # VWAP
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
    df = apply_indicators(data)
    ltp = df['Close'].iloc[-1]
    change = ltp - df['Close'].iloc[-2]
    pct = (change / df['Close'].iloc[-2]) * 100
    
    st.subheader(f"📊 {selected_stock}")
    
    # Header Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("LTP", f"₹{ltp:.2f}", f"{change:.2f} ({pct:.2f}%)")
    m2.metric("Day High", f"₹{df['High'].max():.2f}")
    m3.metric("Day Low", f"₹{df['Low'].min():.2f}")
    m4.metric("Volume", f"{int(df['Volume'].iloc[-1]):,}")

    # --- THE PERFECT HD CANDLE STYLING ---
    rows = 2 if show_rsi else 1
    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.01, 
                        row_heights=[0.8, 0.2] if show_rsi else [1])

    # 🟢 BULLISH GREEN & 🔴 BEARISH RED (Perfect Shades)
    bull_color = '#00FF00' # Bright Green
    bear_color = '#FF0000' # Bright Red

    # 1. THE CANDLESTICK TRACE
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name='Price',
        increasing_line_color=bull_color, 
        decreasing_line_color=bear_color,
        increasing_fillcolor=bull_color, 
        decreasing_fillcolor=bear_color,
        line=dict(width=1) # Makes wicks and borders sharp
    ), row=1, col=1)

    # 2. INDICATOR LINES
    if show_indicators:
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA9'], line=dict(color='#00e5ff', width=1.2), name='9 EMA'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA21'], line=dict(color='#ffeb3b', width=1.2), name='21 EMA'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], line=dict(color='#ff9800', width=1.5, dash='dash'), name='VWAP'), row=1, col=1)

    # 3. RSI SUBPLOT
    if show_rsi:
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#b388ff', width=2), name='RSI'), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color=bear_color, row=2, col=1, opacity=0.3)
        fig.add_hline(y=30, line_dash="dash", line_color=bull_color, row=2, col=1, opacity=0.3)

    # --- THE PERFECT LAYOUT ---
    fig.update_layout(
        height=800,
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        showlegend=False,
        margin=dict(l=10, r=50, t=10, b=10),
        plot_bgcolor='#0d1117', # Deeper black for better candle contrast
        paper_bgcolor='#0d1117',
        uirevision=ticker_symbol,
        dragmode='pan'
    )

    fig.update_xaxes(
        showgrid=True, gridwidth=0.5, gridcolor='#2a2e39',
        rangebreaks=[dict(bounds=["sat", "mon"]), dict(bounds=[15.5, 9.25], pattern="hour")] # Hide weekends/night
    )
    fig.update_yaxes(showgrid=True, gridwidth=0.5, gridcolor='#2a2e39', side='right', tickformat='.2f')

    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': False})

    if live_mode:
        time.sleep(30)
        st.rerun()
else:
    st.error("Select a stock to see the perfect chart.")
