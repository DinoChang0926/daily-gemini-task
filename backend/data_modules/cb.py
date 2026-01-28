import json
import os
import subprocess
import sys
import datetime
from datetime import date

# 對照表路徑
BASE_DIR = os.path.dirname(__file__)
MAPPING_FILE = os.path.join(BASE_DIR, "cb_mapping_dynamic.json")
UPDATE_SCRIPT = os.path.abspath(os.path.join(BASE_DIR, "..", "scripts", "update_cb_mapping.py"))

def load_cb_mapping():
    """
    讀取可轉債對照表。
    若檔案不存在或非今日更新，則執行自動更新腳本。
    """
    should_update = False
    
    if not os.path.exists(MAPPING_FILE):
        should_update = True
        print("CB Mapping file not found. Triggering update...")
    else:
        # 檢查檔案修改日期
        mtime = os.path.getmtime(MAPPING_FILE)
        file_date = datetime.datetime.fromtimestamp(mtime).date()
        today = date.today()
        
        if file_date < today:
            should_update = True
            print(f"CB Mapping file is outdated ({file_date}). Triggering update...")

    if should_update:
        try:
            # 呼叫 script 進行更新
            subprocess.run([sys.executable, UPDATE_SCRIPT], check=True)
            print("CB Mapping update completed.")
        except Exception as e:
            print(f"Failed to update CB mapping: {e}")
            # 若更新失敗但舊檔案存在，仍嘗試讀取舊檔案 (降級運作)
            if not os.path.exists(MAPPING_FILE):
                return {}

    # 讀取 JSON
    try:
        with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading CB mapping JSON: {e}")
        return {}

def get_cb_info(stock_id: str, current_price: float = None):
    """
    獲取可轉債資訊。
    優先使用本地對照表 (cb_mapping_dynamic.json)。
    """
    results = {
        "stock_id": stock_id,
        "has_cb": False,
        "cb_list": []
    }

    # 1. 載入對照表 (含自動更新判斷)
    mapping = load_cb_mapping()
    
    # 2. 查找該股票的可轉債
    # JSON 結構: { "stock_id": [ { "cb_id":..., "cb_name":..., "conversion_price":... } ] }
    cb_data_list = mapping.get(str(stock_id))
    
    if cb_data_list:
        results["has_cb"] = True
        for item in cb_data_list:
            cb_info = {
                "cb_id": item["cb_id"],
                "cb_name": item["cb_name"],
                "conversion_price": item["conversion_price"]
            }
            
            # 計算乖離率
            if current_price and item["conversion_price"] > 0:
                conv_price = item["conversion_price"]
                # 乖離率 = (股價 - 轉換價) / 轉換價 * 100%
                deviation = (current_price - conv_price) / conv_price * 100
                cb_info["deviation_rate"] = round(deviation, 2)
            else:
                cb_info["deviation_rate"] = None
                
            results["cb_list"].append(cb_info)

    return results

if __name__ == "__main__":
    # 測試 (假設目前 4763 股價 110)
    print("Testing CB Info for 1101:")
    print(get_cb_info("1101", 30))

