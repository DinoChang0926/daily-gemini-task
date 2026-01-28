import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from utils.stock_analysis import analyze_stock, get_precise_data, get_60m_data, check_gold_wrapped_silver

def generate_mock_df(rows=300):
    dates = [datetime.now() - timedelta(hours=i) for i in range(rows)]
    dates.reverse()
    data = {
        'Open': np.linspace(100, 110, rows),
        'High': np.linspace(102, 112, rows),
        'Low': np.linspace(98, 108, rows),
        'Close': np.linspace(101, 111, rows),
        'Volume': [1000] * rows
    }
    df = pd.DataFrame(data, index=dates)
    return df

def add_mas(df):
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA10'] = df['Close'].rolling(window=10).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    df['MA120'] = df['Close'].rolling(window=120).mean()
    df['MA240'] = df['Close'].rolling(window=240).mean()
    df['VolMA5'] = df['Volume'].rolling(window=5).mean()
    return df

def test_check_gold_wrapped_silver_squeeze():
    # 建立一個符合 SQUEEZE 的情況
    df = generate_mock_df(300)
    # 設定價格讓均線糾結
    # MA60 < (MA5,10,20) < MA120/240
    # 設 MA60 = 100, 短均 = 105, MA120 = 110
    # 我們直接修改最後幾列來控制均線 (雖然均線是算出來的，但為了單元測試邏輯，我們可以 Mock 算好的列)
    df = add_mas(df)
    
    # 手動調整最後一列以符合 SQUEEZE 條件
    # strict_wrapped = MA60 < min(short_mas) and max(short_mas) < upper_val
    # cv_rate < 0.006
    last_idx = df.index[-1]
    prev_idx = df.index[-5]
    
    df.at[last_idx, 'MA60'] = 100
    df.at[prev_idx, 'MA60'] = 99
    
    df.at[last_idx, 'MA5'] = 105
    df.at[last_idx, 'MA10'] = 105.1
    df.at[last_idx, 'MA20'] = 104.9
    
    df.at[last_idx, 'MA120'] = 110
    df.at[prev_idx, 'MA120'] = 111
    df.at[last_idx, 'MA240'] = 108
    df.at[prev_idx, 'MA240'] = 109
    
    df.at[last_idx, 'Close'] = 105.5
    df.at[last_idx, 'Volume'] = 1000
    df.at[last_idx, 'VolMA5'] = 1000
    
    result = check_gold_wrapped_silver(df)
    assert result['status'] == "SQUEEZE"
    assert result['pattern_found'] is True

def test_check_gold_wrapped_silver_breakout():
    df = generate_mock_df(300)
    df = add_mas(df)
    
    last_idx = df.index[-1]
    prev_idx = df.index[-5]
    
    upper_val = 110
    df.at[last_idx, 'MA60'] = 100
    df.at[prev_idx, 'MA60'] = 100
    df.at[last_idx, 'MA120'] = upper_val
    df.at[prev_idx, 'MA120'] = 111
    df.at[last_idx, 'MA240'] = 105
    
    # 短均
    df.at[last_idx, 'MA5'] = 105
    df.at[last_idx, 'MA10'] = 105
    df.at[last_idx, 'MA20'] = 105
    
    # 帶量突破
    df.at[last_idx, 'Close'] = 115 # > 110
    df.at[last_idx, 'Volume'] = 2000
    df.at[last_idx, 'VolMA5'] = 1000 # 2000 > 1000 * 1.2
    
    result = check_gold_wrapped_silver(df)
    assert result['status'] == "BREAKOUT"

def test_analyze_stock_insufficient_data(mocker):
    mock_yf = mocker.patch('utils.stock_analysis.yf.Ticker')
    mock_instance = mock_yf.return_value
    mock_instance.history.return_value = pd.DataFrame() # 空資料
    
    result = analyze_stock("2330", interval="1d")
    assert "error" in result
    assert "資料不足" in result["error"]

def test_analyze_stock_success(mocker):
    df = generate_mock_df(300)
    mock_yf = mocker.patch('utils.stock_analysis.yf.Ticker')
    mock_instance = mock_yf.return_value
    mock_instance.history.return_value = df
    
    result = analyze_stock("2330.TW", interval="1d")
    assert result['stock_id'] == "2330.TW"
    assert 'ma20' in result
    assert 'k' in result
    assert 'd' in result
    assert 'kd_signal' in result
