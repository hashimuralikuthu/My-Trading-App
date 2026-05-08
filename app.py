import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import os
import time

# 1. Page Configuration
st.set_page_config(page_title="Pro Trading Terminal", layout="wide")
st.title("🔴 My Pro Trading Terminal V23 (Total Market Sync)")

# --- V23: LOCAL CSV DATA ENGINE ---
@st.cache_data
def get_local_stock_list():
    file_path = 'EQUITY_L.csv'
    
    # Check if the file is uploaded to GitHub
    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path)
            # Filter to show only Equity series
            df = df[df['SERIES'] == 'EQ'].copy()
            
            # Combine Symbol and Name for a clean search bar
            df['Display Name'] = df['SYMBOL'] + " - " + df['NAME OF COMPANY']
            df['Yahoo Ticker'] = df['SYMBOL'].astype(str) + ".NS"
            
            # Create a dictionary mapping
            return dict(zip(df['Display Name'], df['Yahoo Ticker']))
        except Exception as e:
            st.error(f"Error reading CSV: {e}")
            return {"RELIANCE - Reliance Industries": "RELIANCE.NS"}
    else:
        # Emergency Fallback if the file isn't uploaded properly
        st.error("⚠️ 'EQUITY_L.csv' not found. Please ensure it is uploaded to your GitHub repository in the same folder as this code.")
        return {
            "IDEA - Vodafone Idea": "IDEA.NS",
            "TATASTEEL - Tata Steel": "TATASTEEL.NS",
            "RELIANCE - Reliance Industries": "RELIANCE.NS",
            "ZOMATO - Zomato Limited": "ZOMATO.NS"
        }

# Load the list
stock_dict = get_local_stock_list()
stock_display_names = sorted(list(stock_dict.keys()))

# 2. Sidebar Settings
st.sidebar.header("🎯 Market Explorer")
selected_display_name = st.sidebar.selectbox(
    f"Search Universe: {len(stock_display_names)} Stocks", 
    stock_display_names, 
    index=0
)

# Extract the actual symbol for yfinance
ticker_symbol = stock_dict[selected_display_name]

col1, col2 = st.sidebar.columns(2)
with col1:
    time_period = st.selectbox("Period", ["1d", "5d", "1mo", "3mo", "1y", "max"], index=0)
with col2:
    time_interval = st.selectbox("Candle", ["1m", "5m", "15m", "30m", "1h", "1d"], index=1)

st.sidebar.markdown("---")
st.sidebar.header("🛠️ Technical Tools")
show_sma = st.sidebar.checkbox("20 SMA (Trend)", value=True)
show_ema = st.sidebar.checkbox("50 EMA (Support)", value=False)
show_rsi = st.sidebar.checkbox("RSI (Overbought/Oversold)", value=True)

st.sidebar.markdown("---")
st.sidebar.header("⚡ Live Engine")
live_mode = st.sidebar.toggle("🟢 Enable Live Auto-Update", value=False)
if live_mode:
    st.sidebar.success("Live Mode Active: Updating every 30s")

# 3. Live Dashboard Engine (Using Streamlit Fragment for speed)
@st.fragment(run_every="30s" if live_mode else None)
def display_terminal():
    # Fetch Data
    data = yf.download(tickers=ticker_symbol, period=time_period, interval=time_interval, progress=False)
    
    if data.empty:
        st.error(f"Market data for {ticker_symbol} is currently unavailable. Market may be closed or ticker is invalid.")
        return
        
    # Fix MultiIndex for YFinance
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    # Metrics
    last_price = data['Close'].iloc[-1]
    prev_price = data['Close'].iloc[-2]
    change = last_price - prev_price
    pct_change = (change / prev_price) * 100

    st.subheader(f"📊 {selected_display_name}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("LTP (Live Price)", f"₹{last_price:.2f}", f"{change:.2f} ({pct_change:.2f}%)")
    c2.metric("Day High", f"₹{data['High'].max():.2f}")
    c3.metric("Day Low", f"₹{data['Low'].min():.2f}")
    c4.metric("Volume", f"{data['Volume'].iloc[-1]:,}")

    # Technical Indicators
    data['SMA20'] = data['Close'].rolling(window=20).mean()
    data['EMA50'] = data['Close'].ewm(span=50, adjust=False).mean()
    
    # Wilder's RSI 
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss
    data['RSI'] = 100 - (100 / (1 + rs))

    # Chart Setup
    rows = 2 if show_rsi else 1
    row_heights = [0.7, 0.3] if show_rsi else [1.0]
    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=row_heights)

    bull_color = '#00FF00' 
    bear_color = '#FF0033' 

    # 1. Main Candlestick
    fig.add_trace(go.Candlestick(
        x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], 
        name='Price', increasing_line_color=bull_color, decreasing_line_color=bear_color
    ), row=1, col=1)

    if show_sma:
        fig.add_trace(go.Scatter(x=data.index, y=data['SMA20'], line=dict(color='#FFD700', width=1.5), name='SMA 20'), row=1, col=1)
    if show_ema:
        fig.add_trace(go.Scatter(x=data.index, y=data['EMA50'], line=dict(color='#00E5FF', width=1.5), name='EMA 50'), row=1, col=1)

    # 2. RSI Subplot
    if show_rsi:
        fig.add_trace(go.Scatter(x=data.index, y=data['RSI'], line=dict(color='#B026FF', width=1.5), name='RSI'), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color=bear_color, row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color=bull_color, row=2, col=1)

    # Layout Styling
    fig.update_layout(
        height=750, 
        template="plotly_dark", 
        xaxis_rangeslider_visible=False, 
        margin=dict(l=10, r=10, t=20, b=10),
        plot_bgcolor='#000000',
        paper_bgcolor='#000000',
    )
    
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#1A1A1A') 
    
    st.plotly_chart(fig, use_container_width=True)

# Run the UI
display_terminal()
