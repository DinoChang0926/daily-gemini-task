import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import json

def check_gold_wrapped_silver(df: pd.DataFrame) -> dict:
    """
    金包銀策略判讀邏輯 (僅適用於 60分K).
    V3 Update: 支援「正向金包銀 (多頭)」與「逆向金包銀 (空頭)」雙向判斷。
    """
    latest = df.iloc[-1]
    prev = df.iloc[-5] 
    
    # 0. 趨勢定義 (Trend Definition)
    # 計算 60MA 斜率
    ma60_slope = (latest['MA60'] - prev['MA60']) / prev['MA60']
    
    if ma60_slope > 0.0005:
        ma60_trend = "UP"
    elif ma60_slope < -0.0005:
        ma60_trend = "DOWN"
    else:
        ma60_trend = "FLAT"

    # 1. 均線數據準備
    # 長均線 (120MA / 240MA)
    ma120 = latest['MA120']
    ma240 = latest['MA240']
    ma60 = latest['MA60']
    
    # 短均線糾結度計算
    short_mas = [latest['MA5'], latest['MA10'], latest['MA20']]
    avg_short = sum(short_mas) / 3
    std_dev = (sum([(x - avg_short)**2 for x in short_mas]) / 3)**0.5
    cv_rate = std_dev / avg_short # 變異係數 (糾結率)
    
    # 2. 狀態判斷變數初始化
    status = "NONE"
    desc = "未符合特殊形態特徵。"
    pattern_type = "NONE" # BULL (多) / BEAR (空)
    
    # ==========================================
    # 🐂 多頭金包銀 (Bullish Gold Wrapped in Silver)
    # 結構: 60MA (支撐) < 短均糾結 < 120/240MA (壓力)
    # ==========================================
    upper_limit = max(ma120, ma240)
    
    # 位置判定: 60MA 在下方，短均在中間 (允許 2% 誤差)
    is_bull_pos = (ma60 * 0.98) < avg_short < (upper_limit * 1.02)
    # 趨勢判定: 60MA 必須上揚或走平
    is_bull_trend = ma60_trend in ["UP", "FLAT"]
    
    if is_bull_pos and is_bull_trend:
        pattern_type = "BULL"
        
        # A. 帶量突破 (Breakout)
        if latest['Close'] > upper_limit and latest['Volume'] > latest['VolMA5'] * 1.2:
            status = "BREAKOUT"
            desc = f"【金包銀】帶量破繭而出！突破長均線壓力，多頭主升段訊號。"
            
        # B. 形態瓦解 (Fail)
        elif latest['Close'] < ma60 * 0.98:
            status = "FAIL"
            desc = "【金包銀】多頭形態瓦解，有效跌破生命線 60MA。"
            
        # C. 糾結整理 (Squeeze/Forming)
        elif cv_rate < 0.015:
            strength = "SQUEEZE (紮實)" if cv_rate < 0.006 else "FORMING (醞釀)"
            status = strength.split()[0]
            desc = f"【金包銀】{strength}，短均糾結於 60MA 之上，蓄勢待發。"

    # ==========================================
    # 🐻 逆向金包銀 (Bearish Reverse Gold Wrapped)
    # 結構: 120/240MA (地板) < 短均糾結 < 60MA (蓋頭壓力)
    # ==========================================
    lower_limit = min(ma120, ma240)
    
    # 位置判定: 60MA 在上方，短均在中間 (允許 2% 誤差)
    is_bear_pos = (lower_limit * 0.98) < avg_short < (ma60 * 1.02)
    # 趨勢判定: 60MA 必須下彎或走平
    is_bear_trend = ma60_trend in ["DOWN", "FLAT"]
    
    # 只有在非多頭形態時才檢查空頭 (避免衝突)
    if pattern_type == "NONE" and is_bear_pos and is_bear_trend:
        pattern_type = "BEAR"
        
        # A. 帶量下殺 (Breakdown) - 空頭起跌點
        if latest['Close'] < lower_limit and latest['Volume'] > latest['VolMA5'] * 1.2:
            status = "BEAR_BREAKDOWN"
            desc = f"【逆向金包銀】帶量跌破長均地板！60MA 下彎蓋頭，空頭主跌段開始。"
            
        # B. 空頭形態失敗 (Rebound) - 站回 60MA
        elif latest['Close'] > ma60 * 1.02:
            status = "BEAR_FAIL"
            desc = "【逆向金包銀】空頭形態失效，股價強勢站回 60MA。"
            
        # C. 弱勢整理 (Bearish Squeeze)
        elif cv_rate < 0.015:
            status = "BEAR_SQUEEZE"
            desc = f"【逆向金包銀】空頭醞釀中，短均糾結於 60MA 之下，隨時可能破底。"

    return {
        "pattern_found": status != "NONE",
        "pattern_type": pattern_type, # BULL / BEAR
        "status": status,
        "description": desc,
        "ma60_trend": ma60_trend,
        "convergence_rate": round(float(cv_rate * 100), 3)
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
    
    # --- 演算法優化: 支撐與壓力邏輯 (Refactored) ---
    recent_60 = df.tail(60)
    high_60 = recent_60['High'].max()
    low_60 = recent_60['Low'].min()
    
    curr_price = float(latest['Close'])
    ma20_val = float(latest['MA20'])
    ma20_prev = float(prev['MA20'])
    
    # 1. 尋找「關鍵大量 K 線」 (Banker's Candle)
    # 定義: 近 20 日內，成交量最大且收紅 (Close > Open) 的 K 線
    recent_20 = df.tail(20).copy()
    recent_20['IsRed'] = recent_20['Close'] > recent_20['Open']
    red_candles = recent_20[recent_20['IsRed']]
    
    smart_money_support = None
    if not red_candles.empty:
        # 找成交量最大的一根
        banker_candle = red_candles.loc[red_candles['Volume'].idxmax()]
        smart_money_support = float(banker_candle['Low'])
    
    # 2. 支撐邏輯 (Support)
    # 預設找區間低點
    support_price = low_60
    support_type = "60d_low"
    
    # 強勢股判斷: 股價 > 月線 且 月線翻揚
    if curr_price > ma20_val and ma20_val > ma20_prev:
        # 多頭強勢回檔策略 (Hybrid Decision)
        if smart_money_support:
            # 取 月線 與 關鍵大量低點 的最大值 (擇強而守)
            if smart_money_support > ma20_val:
                support_price = smart_money_support
                support_type = "smart_money_low"
            else:
                support_price = ma20_val
                support_type = "ma20"
        else:
            support_price = ma20_val
            support_type = "ma20"
        
    # 3. 壓力邏輯 (Resistance)
    # 預設找區間高點
    resist_price = high_60
    resist_type = "60d_high"
    
    # 創新高判斷: 若收盤價已接近或突破 60日高點
    if curr_price >= high_60 * 0.99:
        resist_price = curr_price * 1.1 # 預設漲停板價作為目標
        resist_type = "blue_sky"

    # 4. 防呆檢查 (Sanity Check)
    # 防止支撐壓力過近或倒掛
    if resist_price <= support_price * 1.01:
        # 強制拉開空間
        resist_price = max(resist_price, support_price * 1.05)
        if support_price > curr_price * 0.95:
             support_price = support_price * 0.95

    # 5. 量能濾網 (Volume Filter for Breakdown)
    breakdown_signal = "NONE"
    if curr_price < support_price:
        vol_ma5 = float(latest['VolMA5'])
        curr_vol = float(latest['Volume'])
        if vol_ma5 > 0:
            vol_ratio = curr_vol / vol_ma5
            if vol_ratio > 1.5:
                breakdown_signal = "TRUE_BREAKDOWN" # 帶量真跌破
            elif vol_ratio < 1.0:
                breakdown_signal = "WASH_SALE" # 量縮假跌破
            else:
                breakdown_signal = "BREAKDOWN" # 一般跌破

    output_data = {
        "stock_id": target_symbol,
        "date": latest.name.strftime('%Y-%m-%d %H:%M'),
        "interval": interval,
        "close": round(curr_price, 2),
        "ma5": round(float(latest['MA5']), 2) if not pd.isna(latest['MA5']) else None,
        "ma10": round(float(latest['MA10']), 2) if not pd.isna(latest['MA10']) else None,
        "ma20": round(ma20_val, 2),
        "ma60": round(float(latest['MA60']), 2),
        "ma120": round(float(latest['MA120']), 2) if not pd.isna(latest['MA120']) else None,
        "ma240": round(float(latest['MA240']), 2) if not pd.isna(latest['MA240']) else None,
        "support_price": round(float(support_price), 2),
        "resist_price": round(float(resist_price), 2),
        "support_type": support_type,
        "resist_type": resist_type,
        "smart_money_support": round(smart_money_support, 2) if smart_money_support else None,
        "breakdown_signal": breakdown_signal,
        "short_term_support": round(float(latest['MA5']), 2) if not pd.isna(latest['MA5']) else None,
        "trend_support": round(ma20_val, 2), # 趨勢支撐預設看月線
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
    output_data["strategy_gold_silver"] = None
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
