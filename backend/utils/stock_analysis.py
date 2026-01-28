import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import json

def check_gold_wrapped_silver(df: pd.DataFrame) -> dict:
    """
    金包銀策略判讀邏輯 (僅適用於 60分K).
    """
    latest = df.iloc[-1]
    prev = df.iloc[-5] # 比較前 5 根 K 棒判斷趨勢
    
    # 1. 銀 (外層)
    # 上壓力: 120MA 或 240MA (需下壓)
    ma120_down = latest['MA120'] < prev['MA120']
    ma240_down = latest['MA240'] < prev['MA240']
    upper_ma = "MA120" if latest['MA120'] > latest['MA240'] else "MA240"
    upper_val = latest[upper_ma]
    is_upper_pressing = ma120_down or ma240_down
    
    # 下支撐: 60MA (需上揚或走平)
    is_lower_supporting = latest['MA60'] >= prev['MA60'] * 0.998 # 容許微幅走平
    
    # 2. 金 (內層糾結)
    # 5, 10, 20 MA 是否靠得很近 (標準差 < 均價的 0.5%)
    short_mas = [latest['MA5'], latest['MA10'], latest['MA20']]
    avg_short = sum(short_mas) / 3
    std_dev = (sum([(x - avg_short)**2 for x in short_mas]) / 3)**0.5
    is_clumping = (std_dev / avg_short) < 0.005 # 糾結比例
    
    # 3. 判斷位置: 60MA < 短均 < 120/240MA
    # 嚴格條件: 全數短均線都在 60MA 之上，且在壓力之下
    strict_wrapped = latest['MA60'] < min(short_mas) and max(short_mas) < upper_val
    
    # 寬鬆條件 (Forming): 允許短均暫時跌破 60MA (2% 緩衝)，或暫時突破壓力 (2% 緩衝)
    # 代表形態正在醞釀，尚未完全收斂
    loose_wrapped = (latest['MA60'] * 0.98) < avg_short < (upper_val * 1.02)

    # 4. 判斷狀態
    status = "NONE"
    desc = "未符合金包銀特徵。"
    
    # 計算糾結率百分比
    cv_rate = std_dev / avg_short
    
    # A. 帶量突破 (最強訊號)
    if loose_wrapped and latest['Close'] > upper_val and latest['Volume'] > latest['VolMA5'] * 1.2:
        status = "BREAKOUT"
        desc = f"【金包銀】帶量破繭而出！突破 {upper_ma} 壓力位，短均發散轉強。"
        
    # B. 形態瓦解
    elif latest['Close'] < latest['MA60'] * 0.98: # 真跌破
        status = "FAIL"
        desc = "【金包銀】形態瓦解，有效跌破生命線 60MA。"
        
    # C. 標準整理 (Squeeze) - 嚴格定義
    elif strict_wrapped and cv_rate < 0.006:
        status = "SQUEEZE"
        desc = f"【金包銀】結構紮實 (Squeeze)，短均緊密糾結於 {upper_ma} 與 60MA 之間，隨時可能變盤。"

    # D. 初入/醞釀中 (Forming) - 寬鬆定義
    elif loose_wrapped and cv_rate < 0.015:
        status = "FORMING"
        desc = f"【金包銀】形態醞釀中 (Forming)，短均線開始收斂，關注能否站穩 60MA 並挑戰 {upper_ma}。"
            
    return {
        "pattern_found": status != "NONE",
        "status": status,
        "description": desc,
        "upper_ma_type": upper_ma,
        "upper_ma_val": round(float(upper_val), 2),
        "lower_ma_val": round(float(latest['MA60']), 2),
        "convergence_rate": round(float(std_dev / avg_short * 100), 3)
    }

def analyze_stock(ticker_symbol: str, interval: str = "1d") -> dict:
    """
    通用股票分析函式，支援不同時間週期 (Polymorphic Support).
    """
    def fetch_data(symbol, intv):
        s = yf.Ticker(symbol)
        d = s.history(period="1y" if "1d" in intv else "6mo", interval=intv)
        return s, d

    # 處理股票代號自動偵測 (.TW / .TWO)
    target_symbol = ticker_symbol
    df = pd.DataFrame()
    
    if ticker_symbol.isdigit():
        # 採取由上市到上櫃的嘗試策略
        for suffix in [".TW", ".TWO"]:
            tmp_symbol = f"{ticker_symbol}{suffix}"
            print(f"嘗試獲取 {tmp_symbol} 數據 (Interval: {interval})...")
            _, tmp_df = fetch_data(tmp_symbol, interval)
            if not tmp_df.empty and len(tmp_df) >= 20:
                df = tmp_df
                target_symbol = tmp_symbol
                break
            print(f"  - {tmp_symbol} 資料不適用")
    else:
        print(f"嘗試獲取 {target_symbol} 數據 (Interval: {interval})...")
        _, df = fetch_data(target_symbol, interval)

    if df.empty or len(df) < 20: 
        return {
            "error": "資料不足，無法計算技術指標 (需至少 20 根 K 棒)", 
            "interval": interval,
            "stock_id": ticker_symbol
        }

    # 計算所有需要的均線
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA10'] = df['Close'].rolling(window=10).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    df['MA120'] = df['Close'].rolling(window=120).mean()
    df['MA240'] = df['Close'].rolling(window=240).mean()
    df['VolMA5'] = df['Volume'].rolling(window=5).mean()

    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    # 區間極值
    recent_60_bars = df.tail(60)
    high_60 = recent_60_bars['High'].max()
    low_60 = recent_60_bars['Low'].min()
    
    # Fibonacci
    range_delta = high_60 - low_60
    support_price = round(high_60 - (range_delta * 0.618), 2)
    resist_price = round(low_60 + (range_delta * 0.382), 2)

    output_data = {
        "stock_id": target_symbol,
        "date": latest.name.strftime('%Y-%m-%d %H:%M'),
        "interval": interval,
        "close": round(float(latest['Close']), 2),
        "ma5": round(float(latest['MA5']), 2) if not pd.isna(latest['MA5']) else None,
        "ma10": round(float(latest['MA10']), 2) if not pd.isna(latest['MA10']) else None,
        "ma20": round(float(latest['MA20']), 2),
        "ma60": round(float(latest['MA60']), 2),
        "ma120": round(float(latest['MA120']), 2) if not pd.isna(latest['MA120']) else None,
        "ma240": round(float(latest['MA240']), 2) if not pd.isna(latest['MA240']) else None,
        "support_price": support_price,
        "resist_price": resist_price,
        "volume": int(latest['Volume']),
        "vol_ma5": int(latest['VolMA5'])
    }
    
    # 計算 KD 值 (Period=9)
    # RSV = (Close - Lowest_Low_9) / (Highest_High_9 - Lowest_Low_9) * 100
    low_min = df['Low'].rolling(window=9).min()
    high_max = df['High'].rolling(window=9).max()
    
    # 防止除以零
    rsv = (df['Close'] - low_min) / (high_max - low_min) * 100
    rsv = rsv.fillna(50) # 缺值補 50
    
    # 計算 K, D (平滑參數=3)
    # K = 2/3 * Prev_K + 1/3 * RSV
    # D = 2/3 * Prev_D + 1/3 * K
    k_values = [50] # 初始值
    d_values = [50]
    
    for r in rsv:
        k = (2/3) * k_values[-1] + (1/3) * r
        d = (2/3) * d_values[-1] + (1/3) * k
        k_values.append(k)
        d_values.append(d)
        
    # 移除初始的 50
    k_values = k_values[1:]
    d_values = d_values[1:]
    
    output_data["k"] = round(k_values[-1], 2)
    output_data["d"] = round(d_values[-1], 2)
    
    # KD 訊號判讀
    kd_signal = "NEUTRAL"
    k_curr = k_values[-1]
    d_curr = d_values[-1]
    k_prev = k_values[-2]
    d_prev = d_values[-2]
    
    # 1. 高檔鈍化 (High Passivation): K, D 都維持在 80 以上
    # 表示多頭強勢，但也需警戒乖離過大
    if k_curr >= 80 and d_curr >= 80:
        kd_signal = "HIGH_PASSIVATION"
        
    # 2. 低檔鈍化 (Low Passivation): K, D 都維持在 20 以下
    elif k_curr <= 20 and d_curr <= 20:
        kd_signal = "LOW_PASSIVATION"
        
    # 3. 黃金交叉 (Golden Cross): K 向上突破 D
    elif k_prev < d_prev and k_curr > d_curr:
        kd_signal = "GOLDEN_CROSS"
        
    # 4. 死亡交叉 (Dead Cross): K 向下突破 D
    elif k_prev > d_prev and k_curr < d_curr:
        kd_signal = "DEAD_CROSS"
        
    output_data["kd_signal"] = kd_signal
    
    # 如果是 60分K，執行金包銀策略判斷
    if interval == "60m" and len(df) >= 240:
        output_data["strategy_gold_silver"] = check_gold_wrapped_silver(df)

    print(f"已完成 {target_symbol} [{interval}] 分析")
    return output_data

def get_precise_data(ticker_symbol: str) -> dict:
    """
    [Original Interface] 獲取日線資料 (1d)
    保持與現有 main.py 的相容性
    """
    return analyze_stock(ticker_symbol, interval="1d")

def get_60m_data(ticker_symbol: str) -> dict:
    """
    [New Interface] 獲取 60分K 資料 (60m)
    """
    return analyze_stock(ticker_symbol, interval="60m")

if __name__ == "__main__":
    # 單獨測試金包銀信號
    test_stocks = ["6541", "3466", "8054", "6805"] # 可以換成您想觀察的股票
    print("=" * 50)
    print("「金包銀」策略單獨測試模組")
    print("=" * 50)
    
    for s in test_stocks:
        data = get_60m_data(s)
        if "strategy_gold_silver" in data:
            strat = data["strategy_gold_silver"]
            print(f"【股票: {data['stock_id']}】")
            print(f"  - 狀態: {strat['status']}")
            print(f"  - 描述: {strat['description']}")
            print(f"  - 糾結率: {strat['convergence_rate']}%")
            print(f"  - 上方壓力 ({strat['upper_ma_type']}): {strat['upper_ma_val']}")
            print(f"  - 下方支撐 (MA60): {strat['lower_ma_val']}")
        else:
            print(f"【股票: {s}】 資料不足，無法判定策略位階 (需 240 根 K 棒)。")
        print("-" * 30)
    
    print("測試結束")
