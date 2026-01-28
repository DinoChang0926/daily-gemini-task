from FinMind.data import DataLoader
import pandas as pd
from datetime import datetime, timedelta
try:
    from . import futures_mapping
except ImportError:
    import futures_mapping

def get_futures_info(stock_id: str):
    """
    透過 FinMind 獲取個股期貨數據 (收盤價與 OI)。
    使用 static mapping 找出對應期貨代號。
    自動篩選當日交易量最大或近月合約。
    """
    results = {
        "stock_id": stock_id,
        "futures_id": None,
        "close": 0,
        "open_interest": 0,
        "date": None
    }

    try:
        dl = DataLoader()
        
        # 1. 透過代號查找期貨代號
        futures_id = futures_mapping.get_futures_id(stock_id)
        
        if not futures_id:
             # print(f"No futures found for {stock_id}")
             pass
        else:
            # 獲取近五天的資料
            start_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
            
            df = dl.taiwan_futures_daily(
                futures_id=futures_id,
                start_date=start_date
            )
            
            if not df.empty:
                # 取得最新日期
                latest_date = df['date'].max()
                today_df = df[df['date'] == latest_date].copy()
                
                # 資料處理：確保數值型別正確
                today_df['volume'] = pd.to_numeric(today_df['volume'], errors='coerce').fillna(0)
                today_df['open_interest'] = pd.to_numeric(today_df['open_interest'], errors='coerce').fillna(0)
                today_df['close'] = pd.to_numeric(today_df['close'], errors='coerce').fillna(0)
                
                # 篩選邏輯：Volume DESC, OI DESC
                # 先過濾掉收盤價為 0
                valid_close_df = today_df[today_df['close'] > 0]
                if not valid_close_df.empty:
                    today_df = valid_close_df

                today_df = today_df.sort_values(by=['volume', 'open_interest'], ascending=[False, False])
                
                target_row = today_df.iloc[0]
                
                results["futures_id"] = futures_id
                results["close"] = float(target_row['close'])
                results["open_interest"] = int(target_row['open_interest'])
                results["date"] = target_row['date']

    except Exception as e:
        print(f"Error fetching Futures data: {e}")

    return results

if __name__ == "__main__":
    # 測試
    print(get_futures_info("1605"))
