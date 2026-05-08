import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import os
import time

# 1. Page Configuration
st.set_page_config(page_title="Intraday Pro Terminal", layout="wide")
st.title("🔴 Pro Trading Terminal V31 (Master Charts)")

# --- V31: DATA ENGINE ---
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
st.sidebar.header("🛠️ Chart Indicators")
show_ema9 = st.sidebar.checkbox("9 EMA (Signal)", value=True)
show_ema21 = st.sidebar.checkbox("21 EMA (Trend)", value=True)
show_vwap = st.sidebar.checkbox("VWAP (Intraday)", value=True)
show_rsi = st.sidebar.checkbox("RSI", value=True)

st.sidebar.markdown("---")
live_mode = st.sidebar.toggle("🟢 Enable Live Auto-Update", value=False)

# 3. Technical Calculation Engine
def apply_indicators(df):
    if df is None or df.empty: return None
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    
    # EMAs
    df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
    
    # VWAP
    v = df['Volume'].values
    p = (df['High'] + df['Low'] + df['Close']).values / 3
    df['VWAP'] = (p * v).cumsum() / v.cumsum()
    
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
    
    # Price Metrics
    ltp = df['Close'].iloc[-1]
    change = ltp - df['Close'].iloc[-2]
    pct = (change / df['Close'].iloc[-2]) * 100
    
    st.subheader(f"📊 {selected_stock}")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Current Price", f"₹{ltp:.2f}", f"{change:.2f} ({pct:.2f}%)")
    m2.metric("Day High", f"₹{df['High'].max():.2f}")
    m3.metric("Day Low", f"₹{df['Low'].min():.2f}")
    m4.metric("Live Vol", f"{df['Volume'].iloc[-1]:,}")

    # --- THE BEST CANDLE STYLING ---
    rows = 2 if show_rsi else 1
    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.8, 0.2] if show_rsi else [1])

    # Professional Colors
    up_fill = '#26a69a'   # TradingView Green
    up_line = '#004d40'   # Deep Green Border
    down_fill = '#ef5350' # TradingView Red
    down_line = '#880e4f' # Deep Red Border

    # 1. THE CANDLESTICK TRACE
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name='Price',
        increasing_fillcolor=up_fill, increasing_line_color=up_line,
        decreasing_fillcolor=down_fill, decreasing_line_color=down_line,
        line=dict(width=1) # Sharper Wicks
    ), row=1, col=1)

    # Moving Averages (Smooth hugging lines)
    if show_ema9:
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA9'], line=dict(color='#00e5ff', width=1.5), name='9 EMA'), row=1, col=1)
    if show_ema21:
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA21'], line=dict(color='#ffeb3b', width=1.5), name='21 EMA'), row=1, col=1)
    if show_vwap:
        fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], line=dict(color='#ff9800', width=1.5, dash='dash'), name='VWAP'), row=1, col=1)

    # Current Price Marker Line
    fig.add_hline(y=ltp, line_width=1, line_dash="dash", line_color="white", row=1, col=1, opacity=0.5)

    # 2. RSI Subplot
    if show_rsi:
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#9c27b0', width=2), name='RSI'), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="#ef5350", row=2, col=1, opacity=0.3)
        fig.add_hline(y=30, line_dash="dash", line_color="#26a69a", row=2, col=1, opacity=0.3)

    # --- THE "PERFECT" LAYOUT SETTINGS ---
    fig.update_layout(
        height=800,
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        showlegend=False,
        margin=dict(l=10, r=50, t=10, b=10), # Added space on right for price
        plot_bgcolor='#131722',
        paper_bgcolor='#131722',
        uirevision=ticker_symbol,
        dragmode='pan'
    )

    fig.update_xaxes(
        showgrid=True, gridwidth=0.5, gridcolor='#2a2e39',
        rangebreaks=[dict(bounds=["sat", "mon"]), dict(bounds=[15.5, 9.25], pattern="hour")]
    )
    fig.update_yaxes(showgrid=True, gridwidth=0.5, gridcolor='#2a2e39', side='right', tickformat='.2f')

    # Add Price Label on right axis
    fig.add_annotation(
        xref="paper", yref="y", x=1.02, y=ltp,
        text=f"<b>{ltp:.2f}</b>",
        showarrow=False, bgcolor=up_fill if change >= 0 else down_fill,
        font=dict(color="white", size=12), bordercolor="white", borderpad=4,
        row=1, col=1
    )

    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

    if live_mode:
        time.sleep(30)
        st.rerun()
else:
    st.error("Select a stock to view the master chart.")
