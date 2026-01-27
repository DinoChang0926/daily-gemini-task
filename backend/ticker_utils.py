from FinMind.data import DataLoader
import pandas as pd

def get_ticker_by_name(name: str) -> str:
    """
    透過中文名稱取得台股股票代號。
    
    Args:
        name: 股票中文名稱 (例如 "台積電")
    
    Returns:
        股票代碼 (格式: "2330.TW" 或 "8299.TWO")，若找不到則回傳錯誤訊息。
    """
    try:
        dl = DataLoader()
        # 獲取所有上市上櫃股票列表
        df = dl.taiwan_stock_info() 
        
        # 過濾名稱 (精確比對)
        match = df[df['stock_name'] == name]
        
        if not match.empty:
            ticker = match.iloc[0]['stock_id']
            # yfinance 格式轉換：上市加 .TW，上櫃加 .TWO
            market = match.iloc[0]['type']
            suffix = ".TW" if market == "twse" else ".TWO"
            return f"{ticker}{suffix}"
            
        return "【資料不足，無法確認】"
    except Exception as e:
        return f"【查詢發生錯誤: {str(e)}】"

if __name__ == "__main__":
    # 單元測試
    test_names = ["台積電", "欣銓", "無此股票"]
    print("=== Ticker Utils 測試 ===")
    for n in test_names:
        result = get_ticker_by_name(n)
        print(f"名稱: {n} -> 代號: {result}")
    print("=== 測試結束 ===")
