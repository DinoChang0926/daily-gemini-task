import requests
from bs4 import BeautifulSoup
import json
import os
import re
from FinMind.data import DataLoader
import pandas as pd

URL = "https://www.taifex.com.tw/cht/4/contractName"
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "data_modules", "futures_mapping_static.json")

def normalize(name):
    """移除干擾字元以進行比對"""
    return re.sub(r'\(.*?\)|（.*?）|期貨|選擇權|1000股', '', name).strip()

def scrape_futures_mapping():
    print(f"正在從期交所爬取最新代號對照表: {URL}")
    try:
        # 1. 取得 FinMind 股票清單 (用於平衡名稱與代號)
        print("正在獲取 FinMind 股票清單以進行名稱對應...")
        dl = DataLoader()
        stock_info = dl.taiwan_stock_info()
        name_to_id = {normalize(row['stock_name']): row['stock_id'] for _, row in stock_info.iterrows()}

        # 2. 爬取期交所
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(URL, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            print(f"無法存取網頁: {response.status_code}")
            return
            
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', {'class': 'table_c'})
        if not table:
            print("找不到資料表格 (table_c)")
            return
            
        mapping = {}
        rows = table.find_all('tr')
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 3:
                continue
                
            ticker = cols[1].get_text(strip=True)
            full_name = cols[2].get_text(strip=True)
            
            # 只處理長度 2 或 3 的代號
            if not (2 <= len(ticker) <= 3):
                continue
            
            clean_name = normalize(full_name)
            stock_id = name_to_id.get(clean_name)
            
            if stock_id:
                # 策略：優先選擇以 F 結尾的代號 (代表期貨)
                # 或是長度為 2 的代號 (之後會補 F)
                is_futures = ticker.endswith('F') or len(ticker) == 2
                
                # 若尚未紀錄，或當前是期貨代號 (結尾為 F)
                if stock_id not in mapping or is_futures:
                    final_ticker = ticker
                    if len(ticker) == 2:
                        final_ticker = ticker + "F"
                    
                    # 避免被選擇權 (結尾通常非 F) 蓋掉
                    if final_ticker.endswith('F'):
                        mapping[stock_id] = final_ticker

        if mapping:
            # 確保目錄存在
            os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(mapping, f, ensure_ascii=False, indent=2)
            print(f"成功更新對照表，共 {len(mapping)} 筆資料，儲存至: {OUTPUT_FILE}")
            
            # 驗證幾個關鍵點
            print(f"驗證 2330: {mapping.get('2330')}")
            print(f"驗證 2002: {mapping.get('2002')}")
        else:
            print("未抓取到任何有效對應。")

    except Exception as e:
        print(f"發生錯誤: {e}")

if __name__ == "__main__":
    scrape_futures_mapping()
