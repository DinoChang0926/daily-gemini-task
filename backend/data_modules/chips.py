import requests
import pandas as pd
from datetime import datetime
import urllib3

# 忽略不安全的連線警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_twse_chips(date_str: str, stock_id: str):
    """
    從 TWSE 獲取特定日期的籌碼資料 (投信買賣超與融資餘額)。
    date_str 格式: YYYYMMDD
    stock_id 格式: 2330
    """
    results = {
        "date": date_str,
        "stock_id": stock_id,
        "it_buy": 0,    # 投信買進
        "it_sell": 0,   # 投信賣出
        "it_net": 0,    # 投信買賣超
        "margin_balance": 0,     # 融資本日餘額
        "margin_prev_balance": 0, # 融資前日餘額
        "margin_diff": 0          # 融資增減
    }

    # 1. 投信買賣超 (T86)
    t86_url = f"https://www.twse.com.tw/rwd/zh/fund/T86?date={date_str}&selectType=ALL&response=json"
    try:
        resp = requests.get(t86_url, timeout=10, verify=False)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("stat") == "OK" and "data" in data:
                for row in data["data"]:
                    if row[0].strip() == stock_id:
                        # 格式可能變動，這裡嘗試標準位置
                        # T86: 代號(0), 名稱(1), 外資買(2), 外資賣(3), 外資差(4), 
                        # 外資自營買(5), 外資自營賣(6), 外資自營差(7)
                        # 投信買(8), 投信賣(9), 投信差(10)
                        results["it_buy"] = int(row[8].replace(",", ""))
                        results["it_sell"] = int(row[9].replace(",", ""))
                        results["it_net"] = int(row[10].replace(",", ""))
                        break
    except Exception as e:
        print(f"Error fetching T86: {e}")

    # 2. 融資餘額 (MI_MARGN)
    margin_url = f"https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?date={date_str}&selectType=STOCK&response=json"
    try:
        resp = requests.get(margin_url, timeout=10, verify=False)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("stat") == "OK" and "tables" in data:
                # MI_MARGN tables[0] 通常是信用交易統計
                # 需尋找含有該股票代號的列表
                # 證交所格式：股票代號(0), 股票名稱(1), 融資買進(2), 融資賣出(3), 現金償還(4), 前日餘額(5), 今日餘額(6)
                target_table = None
                for tbl in data["tables"]:
                    if "data" in tbl and len(tbl["data"]) > 0:
                         # 檢查第一筆是否像股票格式
                         if len(tbl["data"][0]) > 6:
                             target_table = tbl
                             break
                
                if target_table:
                    for row in target_table["data"]:
                        if row[0].strip() == stock_id:
                            results["margin_prev_balance"] = int(row[5].replace(",", ""))
                            results["margin_balance"] = int(row[6].replace(",", ""))
                            results["margin_diff"] = results["margin_balance"] - results["margin_prev_balance"]
                            break
    except Exception as e:
        print(f"Error fetching MI_MARGN: {e}")

    return results

if __name__ == "__main__":
    # 簡單測試 (需有網法連線且當天有開盤)
    test_date = datetime.now().strftime("%Y%m%d")
    print(get_twse_chips("20240126", "2330"))
