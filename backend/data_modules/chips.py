import requests
import pandas as pd
from datetime import datetime
import urllib3

# 忽略不安全的連線警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

STOCK_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Referer": "https://www.tpex.org.tw/",
    "X-Requested-With": "XMLHttpRequest",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
}

def ad_to_roc(date_str: str) -> str:
    """轉換 YYYYMMDD 為 民國年/MM/DD (例如 113/01/26)"""
    try:
        dt = datetime.strptime(date_str, "%Y%m%d")
        roc_year = dt.year - 1911
        return f"{roc_year}/{dt.strftime('%m/%d')}"
    except:
        return ""

def _get_twse_chips(date_str: str, stock_id: str):
    """內部函式：從 TWSE 獲取數據"""
    results = {
        "it_buy": 0, "it_sell": 0, "it_net": 0,
        "margin_balance": 0, "margin_prev_balance": 0, "margin_diff": 0,
        "found": False
    }

    # 1. 投信買賣超 (T86)
    t86_url = f"https://www.twse.com.tw/rwd/zh/fund/T86?date={date_str}&selectType=ALL&response=json"
    try:
        resp = requests.get(t86_url, headers=STOCK_HEADERS, timeout=10, verify=False)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("stat") == "OK" and "data" in data:
                for row in data["data"]:
                    if row[0].strip() == stock_id:
                        # T86: 投信買(8), 投信賣(9), 投信差(10)
                        results["it_buy"] = int(row[8].replace(",", ""))
                        results["it_sell"] = int(row[9].replace(",", ""))
                        results["it_net"] = int(row[10].replace(",", ""))
                        results["found"] = True
                        break
    except Exception as e:
        print(f"Error fetching TWSE T86: {e}")

    # 2. 融資餘額 (MI_MARGN)
    margin_url = f"https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?date={date_str}&selectType=STOCK&response=json"
    try:
        resp = requests.get(margin_url, headers=STOCK_HEADERS, timeout=10, verify=False)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("stat") == "OK" and "tables" in data:
                target_table = None
                for tbl in data["tables"]:
                    if "data" in tbl and len(tbl["data"]) > 0 and len(tbl["data"][0]) > 6:
                        target_table = tbl
                        break
                
                if target_table:
                    for row in target_table["data"]:
                        if row[0].strip() == stock_id:
                            # 融資: 前日(5), 今日(6)
                            results["margin_prev_balance"] = int(row[5].replace(",", ""))
                            results["margin_balance"] = int(row[6].replace(",", ""))
                            results["margin_diff"] = results["margin_balance"] - results["margin_prev_balance"]
                            results["found"] = True
                            break
    except Exception as e:
        print(f"Error fetching TWSE MI_MARGN: {e}")

    return results

def _get_tpex_chips(date_str: str, stock_id: str):
    """內部函式：從 TPEx (櫃買中心) 獲取數據"""
    results = {
        "it_buy": 0, "it_sell": 0, "it_net": 0,
        "margin_balance": 0, "margin_prev_balance": 0, "margin_diff": 0,
        "found": False
    }
    roc_date = ad_to_roc(date_str)
    if not roc_date: return results

    # 1. 投信買賣超 (3insti)
    # 1. 投信買賣超 (3insti)
    inst_url = f"https://www.tpex.org.tw/web/stock/3insti/daily_trade/3itrade_hedge_result.php?l=zh-tw&o=json&se=EW&t=D&d={roc_date}"
    try:
        resp = requests.get(inst_url, headers=STOCK_HEADERS, timeout=10, verify=False)
        if resp.status_code == 200:
            data = resp.json()
            if "aaData" in data:
                for row in data["aaData"]:
                    if row[0].strip() == stock_id:
                        # TPEx: 投信買(10), 投信賣(11), 投信差(12) (索引需視實際API變動調整，目前預設為此)
                        # 注意：TPEx 有時會有千分位
                        results["it_buy"] = int(str(row[10]).replace(",", ""))
                        results["it_sell"] = int(str(row[11]).replace(",", ""))
                        results["it_net"] = int(str(row[12]).replace(",", ""))
                        results["found"] = True
                        break
    except Exception as e:
        print(f"Error fetching TPEx Inst: {e}")

    # 2. 融資餘額 (margin_bal)
    margin_url = f"https://www.tpex.org.tw/web/stock/margin_trading/margin_balance/margin_bal_result.php?l=zh-tw&o=json&d={roc_date}"
    try:
        resp = requests.get(margin_url, headers=STOCK_HEADERS, timeout=10, verify=False)

        if resp.status_code == 200:
            data = resp.json()
            if "aaData" in data:
                for row in data["aaData"]:
                    if row[0].strip() == stock_id:
                        # TPEx 融資: 前日(2), 今日(6)
                        results["margin_prev_balance"] = int(str(row[2]).replace(",", ""))
                        results["margin_balance"] = int(str(row[6]).replace(",", ""))
                        results["margin_diff"] = results["margin_balance"] - results["margin_prev_balance"]
                        results["found"] = True
                        break
    except Exception as e:
        print(f"Error fetching TPEx Margin: {e}")

    return results

def get_twse_chips(date_str: str, stock_id: str):
    """
    通用籌碼獲取函式 (支援 TWSE 與 TPEx)
    先嘗試 TWSE，若找不到資料則嘗試 TPEx
    """
    final_res = {
        "date": date_str,
        "stock_id": stock_id,
        "it_buy": 0, "it_sell": 0, "it_net": 0,
        "margin_balance": 0, "margin_prev_balance": 0, "margin_diff": 0,
        "source": "None"
    }

    # 嘗試 TWSE
    twse_res = _get_twse_chips(date_str, stock_id)
    if twse_res["found"]:
        final_res.update(twse_res)
        final_res["source"] = "TWSE"
        del final_res["found"]
        return final_res

    # 嘗試 TPEx
    # print(f"Stock {stock_id} not found in TWSE, trying TPEx...")
    tpex_res = _get_tpex_chips(date_str, stock_id)
    if tpex_res["found"]:
        final_res.update(tpex_res)
        final_res["source"] = "TPEx"
        del final_res["found"]
        return final_res
    
    del final_res["source"]
    return final_res

if __name__ == "__main__":
    test_date = "20260129" # Metadata time
    # test_date = datetime.now().strftime("%Y%m%d")
    
    # Test 5309 (TPEx) and 2330 (TWSE)
    print(f"Testing 2330 (TWSE) on {test_date}:")
    print(get_twse_chips(test_date, "2330"))
    
    print(f"\nTesting 5309 (TPEx) on {test_date}:")
    print(get_twse_chips(test_date, "5309"))
    
    print(f"\nTesting 8069 (TPEx) 元太 on {test_date}:")
    print(get_twse_chips(test_date, "8069"))

