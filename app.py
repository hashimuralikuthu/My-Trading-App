import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import requests
import io

# 1. Page Configuration
st.set_page_config(page_title="Pro Terminal V14", layout="wide")
st.title("🚀 Pro Trading Terminal V14 (All 2,000+ NSE Stocks)")

# --- THE "NO-FAIL" NSE TICKER ENGINE ---
@st.cache_data(ttl=86400)
def get_all_nse_tickers():
    # Attempt to fetch the live list from NSE
    try:
        # We use a specific session to trick the server into thinking we are a Chrome browser
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.nseindia.com/market-data/live-equity-market"
        }
        
        session = requests.Session()
        # Initial hit to establish cookies
        session.get("https://www.nseindia.com", headers=headers, timeout=10)
        
        # The specific URL for the equity master list
        url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        response = session.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            df = pd.read_csv(io.StringIO(response.text))
            # Clean data: only 'EQ' (Equity) series
            df = df[df['SERIES'] == 'EQ'].copy()
            
            # Format: "COMPANY NAME | SYMBOL" for easier searching
            df['Display Name'] = df['SYMBOL'] + " - " + df['NAME OF COMPANY']
            df['Yahoo Ticker'] = df['SYMBOL'] + ".NS"
            
            # Store in a dictionary
            full_dict = dict(zip(df['Display Name'], df['Yahoo Ticker']))
            return full_dict
        else:
            raise Exception("NSE Server Busy")
            
    except Exception as e:
        # If the server blocks us, we use this large pre-made list as a backup 
        # so you ALWAYS have more than 4 stocks.
        st.error("Live NSE Link Blocked. Check your internet or try again in 5 minutes.")
        return {
            "RELIANCE - Reliance Industries Limited": "RELIANCE.NS",
            "TCS - Tata Consultancy Services Limited": "TCS.NS",
            "HDFCBANK - HDFC Bank Limited": "HDFCBANK.NS",
            "ICICIBANK - ICICI Bank Limited": "ICICIBANK.NS",
            "INFY - Infosys Limited": "INFY.NS",
            "ZOMATO - Zomato Limited": "ZOMATO.NS",
            "ADANIENT - Adani Enterprises Limited": "ADANIENT.NS",
            "TATAMOTORS - Tata Motors Limited": "TATAMOTORS.NS",
            "SBIN - State Bank of India": "SBIN.NS",
            "BHARTIARTL - Bharti Airtel Limited": "BHARTIARTL.NS"
        }

# Initialize stock list
stock_dict = get_all_nse_tickers()
# Sort them alphabetically so the search bar is clean
stock_names = sorted(list(stock_dict.keys()))

# 2. Sidebar Search
st.sidebar.header("🔍 Global Search")
selected_stock = st.sidebar.selectbox(
    f"Search in {len(stock_names)} Stocks", 
    options=stock_names,
    index=0
)

# Convert selection to ticker
ticker_symbol = stock_dict[selected_stock]

# UI Controls
st.sidebar.markdown("---")
col1, col2 = st.sidebar.columns(2)
period = col1.selectbox("Period", ["1d", "5d", "1mo", "1y", "max"], index=0)
interval = col2.selectbox("Interval", ["1m", "5m", "15m", "1h", "1d"], index=1)

# 3. Live Dashboard with Fragment
@st.fragment(run_every="30s")
def live_chart(symbol, name):
    # Fetch Data
    data = yf.download(symbol, period=period, interval=interval, progress=False)
    
    if data.empty:
        st.warning(f"Market data for {symbol} is currently unavailable.")
        return

    # Fix MultiIndex for YFinance
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    # Simple Price Metrics
    last_price = data['Close'].iloc[-1]
    prev_price = data['Close'].iloc[0]
    diff = last_price - prev_price
    pct = (diff / prev_price) * 100

    m1, m2, m3 = st.columns(3)
    m1.metric("LTP", f"₹{last_price:.2f}", f"{pct:.2f}%")
    m2.metric("High", f"₹{data['High'].max():.2f}")
    m3.metric("Low", f"₹{data['Low'].min():.2f}")

    # Build the Plotly Chart
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
    
    # Candlestick
    fig.add_trace(go.Candlestick(
        x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'],
        name="Price"
    ), row=1, col=1)

    # Volume
    fig.add_trace(go.Bar(x=data.index, y=data['Volume'], name="Volume", marker_color='orange'), row=2, col=1)

    fig.update_layout(
        height=700,
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        margin=dict(l=10, r=10, t=10, b=10)
    )
    
    st.plotly_chart(fig, use_container_width=True)

# Run
st.subheader(f"📊 {selected_stock}")
live_chart(ticker_symbol, selected_stock)
