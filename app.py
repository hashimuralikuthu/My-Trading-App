import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import os

# 1. Page Configuration
st.set_page_config(page_title="Pro Terminal V21", layout="wide")
st.title("🔴 Pro Trading Terminal V21 (Full Market Access)")

# --- V21 DATA ENGINE: LOCAL CSV LOADER ---
@st.cache_data
def get_local_nse_tickers():
    file_path = 'EQUITY_L.csv'
    
    # Check if the file actually exists in the folder
    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path)
            # Standard NSE CSV columns: SYMBOL, NAME OF COMPANY, SERIES
            df = df[df['SERIES'] == 'EQ'].copy()
            
            # Create a clean searchable name
            df['Display Name'] = df['SYMBOL'] + " - " + df['NAME OF COMPANY']
            df['Yahoo Ticker'] = df['SYMBOL'] + ".NS"
            
            return dict(zip(df['Display Name'], df['Yahoo Ticker']))
        except Exception as e:
            st.error(f"Error reading CSV: {e}")
            return {"RELIANCE - Reliance Industries": "RELIANCE.NS"}
    else:
        # Emergency Fallback if you haven't uploaded the file yet
        st.warning("⚠️ EQUITY_L.csv not found in folder. Using Top 10 Backup.")
        return {
            "IDEA - Vodafone Idea": "IDEA.NS",
            "TATASTEEL - Tata Steel": "TATASTEEL.NS",
            "TATAGOLD - Tata Gold ETF": "TATAGOLD.NS",
            "RELIANCE - Reliance Industries": "RELIANCE.NS",
            "ZOMATO - Zomato Ltd": "ZOMATO.NS"
        }

stock_dict = get_local_nse_tickers()
stock_list = sorted(list(stock_dict.keys()))

# 2. Sidebar: Professional Search
st.sidebar.header("🎯 Market Search")
# This will now show 2,000+ stocks if the CSV is present
selected_stock = st.sidebar.selectbox(
    f"Search {len(stock_list)} Stocks", 
    stock_list,
    help="Search by Symbol (e.g. IDEA) or Name (e.g. Vodafone)"
)
ticker_symbol = stock_dict[selected_stock]

st.sidebar.markdown("---")
col1, col2 = st.sidebar.columns(2)
time_period = col1.selectbox("Period", ["1d", "5d", "1mo", "1y", "max"], index=0)
time_interval = col2.selectbox("Interval", ["1m", "5m", "15m", "1h", "1d"], index=0)

# 3. Technical Calculation (Wilder's RSI)
def get_indicators(df):
    # RSI Formula: 100 - (100 / (1 + RS))
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0))
    loss = (-delta.where(delta < 0, 0))
    avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

# 4. Live Dashboard Fragment
@st.fragment(run_every="30s")
def render_terminal(symbol, display_name):
    data = yf.download(symbol, period=time_period, interval=time_interval, progress=False)
    
    if data.empty:
        st.error("No live data found for this stock. Market might be closed.")
        return

    # Handle yfinance MultiIndex
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    data = get_indicators(data)
    
    # --- TOP ROW METRICS ---
    last_price = data['Close'].iloc[-1]
    prev_price = data['Close'].iloc[-2]
    change = last_price - prev_price
    pct_change = (change / prev_price) * 100

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("LTP", f"₹{last_price:.2f}", f"{change:.2f} ({pct_change:.2f}%)")
    m2.metric("Day High", f"₹{data['High'].max():.2f}")
    m3.metric("RSI (14)", f"{data['RSI'].iloc[-1]:.1f}")
    m4.metric("Volume", f"{data['Volume'].iloc[-1]:,.0f}")

    # --- ADVANCED PLOTLY CHART ---
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, row_heights=[0.7, 0.3])

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'],
        name="Price", increasing_line_color='#00FF00', decreasing_line_color='#FF0000'
    ), row=1, col=1)

    # RSI
    fig.add_trace(go.Scatter(x=data.index, y=data['RSI'], name="RSI", line=dict(color='#00E5FF', width=2)), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

    fig.update_layout(
        height=800,
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        showlegend=False,
        margin=dict(l=10, r=10, t=20, b=10)
    )
    
    st.plotly_chart(fig, use_container_width=True)

# Start App
st.subheader(f"📊 {selected_stock}")
render_terminal(ticker_symbol, selected_stock)
