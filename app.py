import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd

# 1. Set up the web page
st.set_page_config(page_title="Intraday Trading Dashboard", layout="wide")
st.title("📈 My Trading Dashboard V2")

# 2. Sidebar for user inputs
st.sidebar.header("Trading Settings")

# NEW: Dropdown list of popular NSE stocks
popular_stocks = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", 
    "INFY.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", 
    "TATAMOTORS.NS", "ZOMATO.NS", "SUZLON.NS", "MRF.NS"
]
selected_stock = st.sidebar.selectbox("Select a Popular Stock", popular_stocks)

# NEW: Allow typing a custom symbol if it's not in the dropdown
custom_stock = st.sidebar.text_input("Or Type Custom Symbol (e.g., WIPRO.NS)", "")

# Logic: Use custom typed stock if exists, else use dropdown
if custom_stock:
    ticker_symbol = custom_stock.upper()
else:
    ticker_symbol = selected_stock

time_period = st.sidebar.selectbox("Time Period", ["1d", "5d", "1mo", "3mo", "6mo", "1y"], index=1)
time_interval = st.sidebar.selectbox("Candle Interval", ["1m", "5m", "15m", "30m", "1h", "1d"], index=2)

# 3. Fetch Market Data
@st.cache_data
def load_data(ticker, period, interval):
    data = yf.download(tickers=ticker, period=period, interval=interval)
    return data

st.write(f"Analyzing data for **{ticker_symbol}**...")
data = load_data(ticker_symbol, time_period, time_interval)

# 4. Display the Dashboard
if not data.empty:
    current_price = data['Close'].iloc[-1].item() 
    st.metric(label="Latest Price", value=f"₹{current_price:.2f}")

    st.subheader("Price Action Chart")
    fig = go.Figure(data=[go.Candlestick(x=data.index,
                    open=data['Open'].squeeze(),
                    high=data['High'].squeeze(),
                    low=data['Low'].squeeze(),
                    close=data['Close'].squeeze())])
    
    fig.update_layout(xaxis_rangeslider_visible=False, height=600, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Raw Market Data")
    st.dataframe(data.tail())
else:
    st.error("No data found. Please check the ticker symbol (make sure to add .NS for Indian stocks).")
