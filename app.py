@st.cache_data(ttl=86400)
def get_all_nse_tickers():
    # Try multiple URLs and methods to ensure we get the 2000+ list
    urls = [
        "https://archives.nseindia.com/content/equities/EQUITY_L.csv",
        "https://www.nseindia.com/content/equities/EQUITY_L.csv"
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/csv,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

    session = requests.Session()
    
    for url in urls:
        try:
            # Hit the homepage first to collect required security cookies
            session.get("https://www.nseindia.com", headers=headers, timeout=10)
            
            # Now try to get the CSV
            response = session.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                df = pd.read_csv(io.StringIO(response.text))
                # Only keep main-board equities
                df = df[df['SERIES'] == 'EQ'].copy()
                
                # Format for professional searching
                df['Display Name'] = df['SYMBOL'] + " - " + df['NAME OF COMPANY']
                df['Yahoo Ticker'] = df['SYMBOL'] + ".NS"
                
                return dict(zip(df['Display Name'], df['Yahoo Ticker']))
        except:
            continue # Try next URL if this one fails

    # EMERGENCY BACKUP: If NSE is completely down, use a larger hardcoded list
    # This ensures you never have "only 4" companies
    st.sidebar.error("⚠️ NSE Live List blocked. Using High-Capacity Backup.")
    return {
        "RELIANCE - Reliance Industries": "RELIANCE.NS",
        "TCS - Tata Consultancy Services": "TCS.NS",
        "HDFCBANK - HDFC Bank": "HDFCBANK.NS",
        "ICICIBANK - ICICI Bank": "ICICIBANK.NS",
        "INFY - Infosys": "INFY.NS",
        "ZOMATO - Zomato Limited": "ZOMATO.NS",
        "TATAMOTORS - Tata Motors": "TATAMOTORS.NS",
        "SBIN - State Bank of India": "SBIN.NS",
        "BHARTIARTL - Bharti Airtel": "BHARTIARTL.NS",
        "ITC - ITC Limited": "ITC.NS",
        "ADANIENT - Adani Enterprises": "ADANIENT.NS",
        "WIPRO - Wipro Limited": "WIPRO.NS",
        "HINDALCO - Hindalco Industries": "HINDALCO.NS",
        "TITAN - Titan Company": "TITAN.NS",
        "BAJFINANCE - Bajaj Finance": "BAJFINANCE.NS"
    }
