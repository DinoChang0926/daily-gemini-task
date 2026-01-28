import os
import json
import subprocess
import sys

CACHE_FILE = "futures_mapping_static.json"
_HAS_REFRESHED = False  # 單次執行僅限刷新一次的旗標

def update_mapping_automatically():
    """自動執行爬蟲腳本以更新對照表"""
    print("對照表不存在，嘗試自動更新...")
    try:
        base_dir = os.path.dirname(__file__)
        script_path = os.path.abspath(os.path.join(base_dir, "..", "scripts", "update_futures_mapping.py"))
        # 使用目前的 Python 解譯器執行
        subprocess.run([sys.executable, script_path], check=True)
        print("對照表更新成功。")
        return True
    except Exception as e:
        print(f"自動更新失敗: {e}")
        return False

def get_futures_id(stock_id: str) -> str:
    """
    透過股票代號查詢對應的期貨代號。
    使用靜態對照表 (futures_mapping_static.json)。
    """
    global _HAS_REFRESHED
    market_file = os.path.join(os.path.dirname(__file__), CACHE_FILE)
    
    # 邏輯：讀取 -> 找不到 -> 沒刷過就刷一次 -> 再讀一次
    def read_mapping():
        if not os.path.exists(market_file):
            return None
        try:
            with open(market_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading futures mapping: {e}")
            return None

    mapping = read_mapping()
    futures_id = mapping.get(str(stock_id)) if mapping else None

    # 如果沒找到且還沒刷新過，嘗試刷新一次
    if futures_id is None and not _HAS_REFRESHED:
        if update_mapping_automatically():
            _HAS_REFRESHED = True
            mapping = read_mapping()
            futures_id = mapping.get(str(stock_id)) if mapping else None
        
    return futures_id

def get_futures_id_by_name(stock_name: str) -> str:
    return None

if __name__ == "__main__":
    print("Testing map for '2330':", get_futures_id("2330"))
    print("Testing map for '2002':", get_futures_id("2002"))
