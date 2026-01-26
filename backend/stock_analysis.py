import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import json

def get_precise_data(ticker_symbol: str) -> dict:
    """
    獲取指定股票代號的詳細數據與均線分析 (Get precise stock data and MA analysis).
    Args:
        ticker_symbol: 股票代號 (e.g. "2382" or "2330.TW")
    """
    # 定義內部函數來嘗試獲取數據
    def fetch_data(symbol):
        print(f"嘗試獲取 {symbol} 數據...")
        s = yf.Ticker(symbol)
        d = s.history(period="6mo")
        return s, d

    # 處理股票代號
    target_symbol = ticker_symbol
    
    # 如果是純數字，先預設 .TW
    if ticker_symbol.isdigit():
        target_symbol = f"{ticker_symbol}.TW"
    
    stock, df = fetch_data(target_symbol)

    # 如果抓不到資料 (且原本是純數字輸入)，嘗試切換成 .TWO (上櫃)
    if len(df) < 60 and ticker_symbol.isdigit():
        print(f"{target_symbol} 資料不足或不存在，嘗試切換為 .TWO...")
        target_symbol = f"{ticker_symbol}.TWO"
        stock, df = fetch_data(target_symbol)
    
    if len(df) < 60:
        return "資料不足，無法計算 60MA (可能為下市股票或代號錯誤)"

    # 計算均線
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    df['VolMA5'] = df['Volume'].rolling(window=5).mean()

    # 取得最新一筆與前一筆 (判斷拐頭)
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    # 計算區間極值 (近60交易日，約一季)
    recent_60_days = df.tail(60)
    high_60 = recent_60_days['High'].max()
    low_60 = recent_60_days['Low'].min()
    
    # 計算波浪關鍵點位 (Fibonacci Levels)
    # 多頭回檔支撐 (從最高點回檔 0.618 或 0.5) -> 視為強力支撐區
    range_delta = high_60 - low_60
    support_price = round(high_60 - (range_delta * 0.618), 2)
    
    # 空頭反彈壓力 (從最低點反彈 0.382 或 0.5) -> 視為壓力區
    resist_price = round(low_60 + (range_delta * 0.382), 2)

    # 輸出給 AI 的格式
    # 輸出給 AI 的格式 (JSON)
    print("-" * 30)
    output_data = {
        "stock_id": ticker_symbol,
        "date": latest.name.strftime('%Y-%m-%d'),
        "close": round(float(latest['Close']), 2),
        "ma20": round(float(latest['MA20']), 2),
        "ma60": round(float(latest['MA60']), 2),
        "prev_ma20": round(float(prev['MA20']), 2),
        "prev_ma60": round(float(prev['MA60']), 2),
        "high_60": round(float(high_60), 2),
        "low_60": round(float(low_60), 2),
        "support_price": support_price, # 新增: 系統計算的支撐位
        "resist_price": resist_price,   # 新增: 系統計算的壓力位
        "volume": int(latest['Volume']),
        "vol_ma5": int(latest['VolMA5'])
    }
    
    # print(json.dumps(output_data, indent=4, ensure_ascii=False))
    print(f"已獲取 {ticker_symbol} 數據 (Support: {support_price}, Resist: {resist_price})")
    print("-" * 30)
    
    return output_data

if __name__ == "__main__":
    # 使用範例：輸入股票代號
    data = get_precise_data("8299")
    print(json.dumps(data, indent=4, ensure_ascii=False))
