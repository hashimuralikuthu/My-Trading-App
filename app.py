import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd

# 1. Set up the web page
st.set_page_config(page_title="Intraday Trading Dashboard", layout="wide")
st.title("📈 My Trading Dashboard V1")

# 2. Sidebar for user inputs
st.sidebar.header("Trading Settings")
# Defaulting to an Indian stock, requires .NS for National Stock Exchange
ticker_symbol = st.sidebar.text_input("Enter Ticker Symbol", "RELIANCE.NS")
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
    # Display the latest closing price
    current_price = data['Close'].iloc[-1].item() # .item() extracts the single value cleanly
    st.metric(label="Latest Price", value=f"₹{current_price:.2f}")

    # Draw the Candlestick Chart
    st.subheader("Price Action Chart")
    fig = go.Figure(data=[go.Candlestick(x=data.index,
                    open=data['Open'].squeeze(),
                    high=data['High'].squeeze(),
                    low=data['Low'].squeeze(),
                    close=data['Close'].squeeze())])
    
    # Clean up the chart layout
    fig.update_layout(xaxis_rangeslider_visible=False, height=600, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

    # Show the raw numbers
    st.subheader("Raw Market Data")
    st.dataframe(data.tail())
else:
    st.error("No data found. Please check the ticker symbol (make sure to add .NS for Indian stocks, e.g., TCS.NS or INFY.NS).")