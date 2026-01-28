import requests
import pandas as pd
import json
import os
import urllib3
import io
import datetime

# 忽略 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 設定路徑
BASE_DIR = os.path.dirname(__file__)
DATA_MODULES_DIR = os.path.join(BASE_DIR, "..", "data_modules")
OUTPUT_FILE = os.path.join(DATA_MODULES_DIR, "cb_mapping_dynamic.json")
LOG_FILE = os.path.join(BASE_DIR, "cb_download.log")
URL = "https://cbas16889.pscnet.com.tw/api/MiDownloadExcel/GetExcel_IssuedCB"

def log_message(msg):
    """寫入 Log 檔案"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(f"[{timestamp}] {msg}")

def update_cb_mapping():
    log_message("開始執行可轉債對照表更新...")
    
    try:
        resp = requests.get(URL, verify=False, timeout=60)
        
        if resp.status_code == 404:
            log_message(f"Error 404: 找不到檔案 - {URL}")
            return False
            
        if resp.status_code != 200:
            log_message(f"Error {resp.status_code}: 下載失敗 - {URL}")
            return False
            
        # 解析 Excel
        log_message("下載成功，開始解析 Excel...")
        try:
            df = pd.read_excel(io.BytesIO(resp.content))
            
            # 檢查必要欄位
            required_cols = ['債券代號', '標的債券', '轉換價格', '轉換標的代碼']
            if not all(col in df.columns for col in required_cols):
                 log_message(f"Error: Excel 缺少必要欄位。現有欄位: {df.columns.tolist()}")
                 return False

            # 建構 Mapping
            # 格式: { "stock_id": [ { "cb_id": "...", "cb_name": "...", "price": ... }, ... ] }
            mapping = {}
            count = 0
            
            for _, row in df.iterrows():
                try:
                    # 轉換標的代碼可能有小數點或轉成 float，轉字串處理
                    stock_id = str(row['轉換標的代碼']).strip().split('.')[0]
                    cb_id = str(row['債券代號']).strip()
                    cb_name = str(row['標的債券']).strip()
                    price_raw = row['轉換價格']
                    
                    # 處理價格轉型
                    try:
                        price = float(price_raw)
                    except ValueError:
                        price = 0.0

                    if stock_id not in mapping:
                        mapping[stock_id] = []
                    
                    mapping[stock_id].append({
                        "cb_id": cb_id,
                        "cb_name": cb_name,
                        "conversion_price": price
                    })
                    count += 1
                except Exception as e:
                    continue # 略過錯誤行
            
            # 儲存 JSON
            os.makedirs(DATA_MODULES_DIR, exist_ok=True)
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(mapping, f, ensure_ascii=False, indent=2)
                
            log_message(f"更新成功。共處理 {count} 筆可轉債資料，已儲存至 {OUTPUT_FILE}")
            return True

        except Exception as e:
             log_message(f"Error: 解析 Excel 失敗 - {e}")
             return False

    except Exception as e:
        log_message(f"Error: 請求發生例外 - {e}")
        return False

if __name__ == "__main__":
    update_cb_mapping()
