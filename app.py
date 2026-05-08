import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

# 1. Set up the web page
st.set_page_config(page_title="Intraday Trading Dashboard", layout="wide")
st.title("📈 My Trading Dashboard V3 (Pro Chart)")

# 2. Sidebar for user inputs
st.sidebar.header("Trading Settings")

popular_stocks = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", 
    "INFY.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", 
    "TATAMOTORS.NS", "ZOMATO.NS", "SUZLON.NS", "MRF.NS"
]
selected_stock = st.sidebar.selectbox("Select a Popular Stock", popular_stocks)
custom_stock = st.sidebar.text_input("Or Type Custom Symbol", "")

if custom_stock:
    ticker_symbol = custom_stock.upper()
else:
    ticker_symbol = selected_stock

time_period = st.sidebar.selectbox("Time Period", ["1d", "5d", "1mo", "3mo", "6mo", "1y"], index=2)
time_interval = st.sidebar.selectbox("Candle Interval", ["1m", "5m", "15m", "30m", "1h", "1d"], index=5)

# 3. Fetch Market Data
@st.cache_data
def load_data(ticker, period, interval):
    data = yf.download(tickers=ticker, period=period, interval=interval)
    return data

st.write(f"Analyzing data for **{ticker_symbol}**...")
data = load_data(ticker_symbol, time_period, time_interval)

# 4. Display the Pro Dashboard
if not data.empty:
    current_price = data['Close'].iloc[-1].item() 
    st.metric(label="Latest Price", value=f"₹{current_price:.2f}")

    st.subheader("Advanced Price Action & Volume")

    # Calculate a 20-period Simple Moving Average (SMA)
    data['SMA_20'] = data['Close'].rolling(window=20).mean()

    # Set up a chart with 2 sections: Top for Price, Bottom for Volume
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, subplot_titles=('Price & 20 SMA', 'Volume'),
                        row_width=[0.2, 0.7])

    # 1. Add Custom Candlesticks
    fig.add_trace(go.Candlestick(x=data.index,
                    open=data['Open'].squeeze(),
                    high=data['High'].squeeze(),
                    low=data['Low'].squeeze(),
                    close=data['Close'].squeeze(),
                    name='Price',
                    increasing_line_color='#00ff00', # Bright Green
                    decreasing_line_color='#ff0000'  # Bright Red
                    ), row=1, col=1)

    # 2. Add 20 SMA Line
    fig.add_trace(go.Scatter(x=data.index, y=data['SMA_20'].squeeze(), 
                             line=dict(color='#fdb631', width=2), # Yellow line
                             name='20 SMA'), row=1, col=1)

    # 3. Add Volume Bars
    # Make volume bars green or red based on the candle closing price
    colors = ['#00ff00' if close >= open_price else '#ff0000' for close, open_price in zip(data['Close'].squeeze(), data['Open'].squeeze())]
    
    fig.add_trace(go.Bar(x=data.index, y=data['Volume'].squeeze(), 
                         marker_color=colors, name='Volume'), row=2, col=1)

    # Clean up the layout
    fig.update_layout(
        xaxis_rangeslider_visible=False, 
        xaxis2_rangeslider_visible=False,
        height=750, 
        template="plotly_dark",
        showlegend=False,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Raw Market Data")
    st.dataframe(data.tail())
else:
    st.error("No data found. Please check the ticker symbol (make sure to add .NS for Indian stocks).")
