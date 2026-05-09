import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import requests
import io
import time

# 1. Page Configuration
st.set_page_config(page_title="Master Trading Terminal", layout="wide")
st.title("👑 My Master Terminal V13 (Deep Data Edition)")

# --- ADVANCED NSE TICKER & DATA FETCHING ---
@st.cache_data(ttl=86400)
def get_all_nse_data():
    try:
        url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=15)
        df = pd.read_csv(io.StringIO(r.text))
        
        # Clean column names (NSE CSV has hidden spaces)
        df.columns = df.columns.str.strip()
        df = df[df['SERIES'] == 'EQ']
        
        df['Display Name'] = df['NAME OF COMPANY'] + " (" + df['SYMBOL'] + ")"
        df['Yahoo Ticker'] = df['SYMBOL'].astype(str) + ".NS"
        
        # Create a dictionary holding ALL company details
        stock_data = {}
        for _, row in df.iterrows():
            stock_data[row['Display Name']] = {
                'Ticker': row['Yahoo Ticker'],
                'Name': row['NAME OF COMPANY'],
                'Symbol': row['SYMBOL'],
                'ISIN': row['ISIN NUMBER'],
                'Listing_Date': row['DATE OF LISTING'],
                'Face_Value': row['FACE VALUE']
            }
        return stock_data
    except Exception as e:
        # Fallback data if NSE website is slow
        return {
            "Zomato Limited (ZOMATO)": {
                'Ticker': 'ZOMATO.NS', 'Name': 'Zomato Limited', 'Symbol': 'ZOMATO',
                'ISIN': 'INE758T01015', 'Listing_Date': '23-JUL-2021', 'Face_Value': '1'
            },
            "Reliance Industries Limited (RELIANCE)": {
                'Ticker': 'RELIANCE.NS', 'Name': 'Reliance Industries Limited', 'Symbol': 'RELIANCE',
                'ISIN': 'INE002A01018', 'Listing_Date': '29-NOV-1995', 'Face_Value': '10'
            }
        }

stock_data = get_all_nse_data()
stock_display_names = list(stock_data.keys())

default_index = 0
for i, name in enumerate(stock_display_names):
    if "ZOMATO" in name:
        default_index = i
        break

# 2. Sidebar Settings
st.sidebar.header("🎯 Market Explorer")
selected_display_name = st.sidebar.selectbox("Search Company Name", stock_display_names, index=default_index)

# Get all the details for the selected stock
current_stock_info = stock_data[selected_display_name]
ticker_symbol = current_stock_info['Ticker']

col1, col2 = st.sidebar.columns(2)
with col1:
    time_period = st.selectbox("Period", ["1d", "5d", "1mo", "3mo", "6mo", "1y"], index=0)
with col2:
    time_interval = st.selectbox("Candle", ["1m", "5m", "15m", "30m", "1h", "1d"], index=0)

st.sidebar.markdown("---")
st.sidebar.header("🎨 App Theme")
theme_choice = st.sidebar.radio("Choose Chart Theme", ["Ultra Dark", "Clean White"])

st.sidebar.markdown("---")
st.sidebar.header("🛠️ Technical Tools")
show_sma = st.sidebar.checkbox("20 SMA (Trend)", value=True)
show_ema = st.sidebar.checkbox("50 EMA (Support)", value=False)
show_rsi = st.sidebar.checkbox("RSI (Overbought/Oversold)", value=False)
show_macd = st.sidebar.checkbox("MACD (Momentum)", value=False) 

st.sidebar.markdown("---")
st.sidebar.header("⚡ Live Engine")
live_mode = st.sidebar.toggle("🟢 Enable Live Auto-Update", value=False)
if live_mode:
    st.sidebar.success("Live Mode Active")

# 3. Data Fetching Logic
@st.cache_data(ttl=30)
def load_data(ticker, period, interval):
    try:
        data = yf.download(tickers=ticker, period=period, interval=interval, progress=False)
        if data.empty: return pd.DataFrame()
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        return data
    except:
        return pd.DataFrame()

data = load_data(ticker_symbol, time_period, time_interval)

# 4. Dashboard Visuals
if not data.empty:
    last_price = data['Close'].iloc[-1]
    prev_price = data['Close'].iloc[-2]
    change = last_price - prev_price
    pct_change = (change / prev_price) * 100

    st.subheader(f"📊 {current_stock_info['Name']} ({current_stock_info['Symbol']})")

    # --- NEW: COMPANY INFORMATION EXPANDER ---
    with st.expander("ℹ️ Official Company Details (From NSE EQUITY_L.csv)"):
        i1, i2, i3, i4 = st.columns(4)
        i1.write(f"**NSE Symbol:** {current_stock_info['Symbol']}")
        i2.write(f"**ISIN Number:** {current_stock_info['ISIN']}")
        i3.write(f"**Listing Date:** {current_stock_info['Listing_Date']}")
        i4.write(f"**Face Value:** ₹{current_stock_info['Face_Value']}")
    st.markdown("---")

    c1, c2, c3 = st.columns(3)
    c1.metric("Current Price", f"₹{last_price:.2f}", f"{change:.2f} ({pct_change:.2f}%)")
    c2.metric("Day High", f"₹{data['High'].max():.2f}")
    c3.metric("Day Low", f"₹{data['Low'].min():.2f}")

    # Calculations
    data['SMA20'] = data['Close'].rolling(window=20).mean()
    data['EMA50'] = data['Close'].ewm(span=50, adjust=False).mean()
    
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data['RSI'] = 100 - (100 / (1 + rs))

    exp1 = data['Close'].ewm(span=12, adjust=False).mean()
    exp2 = data['Close'].ewm(span=26, adjust=False).mean()
    data['MACD'] = exp1 - exp2
    data['Signal'] = data['MACD'].ewm(span=9, adjust=False).mean()

    active_subplots = 2 
    if show_rsi: active_subplots += 1
    if show_macd: active_subplots += 1

    row_heights = [0.5] + [0.5 / (active_subplots - 1)] * (active_subplots - 1)
    
    fig = make_subplots(rows=active_subplots, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, row_heights=row_heights)

    current_row = 1

    if theme_choice == "Ultra Dark":
        bull_color, bear_color, bg_color, grid_color, template = '#00FF00', '#FF0033', '#000000', '#1A1A1A', "plotly_dark"
    else:
        bull_color, bear_color, bg_color, grid_color, template = '#00C853', '#FF5252', '#FFFFFF', '#E0E0E0', "plotly_white"

    fig.add_trace(go.Candlestick(
        x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], 
        name='Price',
        increasing_line_color=bull_color, decreasing_line_color=bear_color,
        increasing_fillcolor=bull_color, decreasing_fillcolor=bear_color
    ), row=current_row, col=1)

    if show_sma:
        fig.add_trace(go.Scatter(x=data.index, y=data['SMA20'], line=dict(color='#FFD700', width=2), name='SMA 20'), row=current_row, col=1)
    if show_ema:
        fig.add_trace(go.Scatter(x=data.index, y=data['EMA50'], line=dict(color='#00E5FF', width=2), name='EMA 50'), row=current_row, col=1)
    current_row += 1

    colors = [bull_color if c >= o else bear_color for o, c in zip(data['Open'], data['Close'])]
    fig.add_trace(go.Bar(x=data.index, y=data['Volume'], marker_color=colors, name='Volume'), row=current_row, col=1)
    current_row += 1

    if show_rsi:
        fig.add_trace(go.Scatter(x=data.index, y=data['RSI'], line=dict(color='#B026FF', width=2), name='RSI'), row=current_row, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color=bear_color, row=current_row, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color=bull_color, row=current_row, col=1)
        current_row += 1

    if show_macd:
        fig.add_trace(go.Scatter(x=data.index, y=data['MACD'], line=dict(color='#2962FF', width=2), name='MACD'), row=current_row, col=1)
        fig.add_trace(go.Scatter(x=data.index, y=data['Signal'], line=dict(color='#FF8C00', width=2), name='Signal'), row=current_row, col=1)
        macd_hist = data['MACD'] - data['Signal']
        hist_colors = [bull_color if val >= 0 else bear_color for val in macd_hist]
        fig.add_trace(go.Bar(x=data.index, y=macd_hist, marker_color=hist_colors, name='Histogram'), row=current_row, col=1)

    fig.update_layout(
        height=900 if active_subplots > 2 else 700, 
        template=template, xaxis_rangeslider_visible=False, showlegend=False,
        dragmode='pan', hovermode='x unified', plot_bgcolor=bg_color, paper_bgcolor=bg_color, 
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor=grid_color) 
    
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': True, 'modeBarButtonsToAdd': ['drawline', 'eraseshape'], 'displaylogo': False})

else:
    st.error(f"Error fetching data for {selected_display_name}.")

if live_mode:
    time.sleep(30)
    st.rerun()
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# 1. Setup Page Layout
st.set_page_config(layout="wide", page_title="Intraday Trading Dashboard")
st.title("📈 Intraday Trading Dashboard")

# 2. Sidebar Controls for Interactivity
st.sidebar.header("Chart Settings")
ticker_symbol = st.sidebar.text_input("Ticker Symbol", "AAPL").upper()
interval = st.sidebar.selectbox("Intraday Interval", ["1m", "5m", "15m", "30m", "1h"], index=1)
period = st.sidebar.selectbox("Data Period", ["1d", "5d", "1mo"], index=0)

st.sidebar.header("Indicators")
short_window = st.sidebar.slider("Short Moving Average", min_value=3, max_value=50, value=9)
long_window = st.sidebar.slider("Long Moving Average", min_value=10, max_value=200, value=21)

# 3. Fetch Real Intraday Data
@st.cache_data # Caches the data so it doesn't redownload on every slider move
def load_data(ticker, prd, intv):
    data = yf.download(tickers=ticker, period=prd, interval=intv)
    return data

df = load_data(ticker_symbol, period, interval)

# 4. Check if data exists, then calculate and plot
if df.empty:
    st.error(f"No data found for {ticker_symbol}. Please check the ticker or select a different period.")
else:
    # Calculate Moving Averages
    df['Short_MA'] = df['Close'].rolling(window=short_window).mean()
    df['Long_MA'] = df['Close'].rolling(window=long_window).mean()

    # Create an interactive Candlestick chart using Plotly
    fig = go.Figure()

    # Add Candlesticks
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'], high=df['High'],
        low=df['Low'], close=df['Close'],
        name='Price'
    ))

    # Add Moving Averages
    fig.add_trace(go.Scatter(x=df.index, y=df['Short_MA'], line=dict(color='blue', width=1.5), name=f'{short_window}-Period MA'))
    fig.add_trace(go.Scatter(x=df.index, y=df['Long_MA'], line=dict(color='orange', width=1.5), name=f'{long_window}-Period MA'))

    # Format the chart
    fig.update_layout(
        title=f"{ticker_symbol} - {interval} Chart",
        yaxis_title="Price (USD)",
        xaxis_rangeslider_visible=False, # Hides the messy slider at the bottom
        height=600,
        template="plotly_dark" # Gives it a professional trading terminal look
    )

    # Display the chart
    st.plotly_chart(fig, use_container_width=True)

    # Show raw data in a collapsible section
    with st.expander("View Raw Data"):
        st.dataframe(df.tail(10))
