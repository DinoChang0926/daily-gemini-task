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
    # 加上後綴 (台股加 .TW)
    if not ticker_symbol.endswith('.TW') and ticker_symbol.isdigit():
        ticker_symbol += '.TW'
    
    print(f"正在獲取 {ticker_symbol} 精確數據...")
    stock = yf.Ticker(ticker_symbol)
    
    # 抓取足夠計算 60MA 的歷史資料 (抓 6 個月確保足夠)
    df = stock.history(period="6mo")
    
    if len(df) < 60:
        return "資料不足，無法計算 60MA"

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
        "volume": int(latest['Volume']),
        "vol_ma5": int(latest['VolMA5'])
    }
    
    # print(json.dumps(output_data, indent=4, ensure_ascii=False))
    print(f"已獲取 {ticker_symbol} 數據")
    print("-" * 30)
    
    return output_data

if __name__ == "__main__":
    # 使用範例：輸入股票代號
    data = get_precise_data("2382")
    print(json.dumps(data, indent=4, ensure_ascii=False))
