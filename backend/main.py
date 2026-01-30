import os
import re
import json
from datetime import datetime
from flask import Flask, request, jsonify
from google import genai
from google.genai import types
from dotenv import load_dotenv
from google.genai.types import GenerateContentConfig, Tool, GoogleSearch 
from utils.stock_analysis import get_precise_data, get_60m_data
from utils.ticker_utils import get_ticker_by_name
# from data_modules.chips import get_twse_chips # Removed
from data_modules.cb import get_cb_info

# 1. 載入環境變數
load_dotenv(override=True)
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "storied-phalanx-239007")
LOCATION = "us-central1"
MODEL_NAME = os.environ.get("MODEL_NAME", "gemini-2.0-flash-001") 
API_SECRET = os.environ.get("API_SECRET")

app = Flask(__name__)

# 綁定 Gunicorn Logger (確保 Cloud Run 能看到日誌)
import logging
gunicorn_logger = logging.getLogger('gunicorn.error')
app.logger.handlers = gunicorn_logger.handlers
app.logger.setLevel(gunicorn_logger.level)

# 應用程式啟動時預熱快取
print("Warming up stock cache...")
try:
    get_ticker_by_name("台積電")
    print("Stock cache warmed up successfully.")
except Exception as e:
    print(f"Warning: Cache warming failed: {e}")

def read_prompt_file():
    """
    讀取 prompt.txt
    回傳: (content, error_message)
    """
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up one level to find prompt folder
        root_dir = os.path.dirname(base_dir)
        file_path = os.path.join(root_dir, 'prompt', 'prompt.txt')
        
        if not os.path.exists(file_path):
            return None, "錯誤: 找不到 prompt.txt 檔案"
            
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read(), None
    except Exception as e:
        return None, f"讀取 Prompt 發生錯誤: {str(e)}"

@app.route('/ticker', methods=['POST'])
def ticker_endpoint():
    """
    透過股票名稱查詢代碼的 API 端點
    Payload: { "name": "台積電" }
    """
    try:
        data = request.get_json(silent=True)
        if not data or "name" not in data:
            return jsonify({"error": "Missing 'name' in payload"}), 400
            
        name = data.get("name", "")
        ticker = get_ticker_by_name(name)
        
        return jsonify({"name": name, "ticker": ticker})
    except Exception as e:
         return jsonify({"error": str(e)}), 500

@app.route('/task', methods=['POST'])
def execute_task():
    """
    核心分析任務端點
    執行流程: 接收請求 -> 爬取數據(日線+60分+CB) -> 合併數據 -> Gemini 分析 -> 回傳
    """
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Empty payload"}), 400

        user_question = data.get("question", "")
        system_prompt = data.get("system_prompt", "") # 前端可覆蓋 prompt
            
        if not user_question:
            return jsonify({"error": "Question is empty"}), 400

        # --- 步驟 1: 數據獲取與合併 (Data Fetching & Merging) ---
        # 建立一個空字典，準備將所有來源的數據合併成單一 JSON
        stock_data_context = {} 
        match = re.search(r'(\d{4})', user_question)
        
        if match:
            ticker = match.group(1)
            app.logger.info(f"Detected Ticker: {ticker}, fetching data...")
            
            try:
                # A. 獲取日線數據 (基礎數據)
                daily_data = get_precise_data(ticker)
                if daily_data and "error" not in daily_data:
                    stock_data_context.update(daily_data)
                
                # B. 獲取 60分K 數據 (提取金包銀策略)
                # 注意: 我們只提取 'strategy_gold_silver'，避免覆蓋日線的 MA 數值
                m60_data = get_60m_data(ticker)
                if m60_data and "strategy_gold_silver" in m60_data:
                    stock_data_context["strategy_gold_silver"] = m60_data["strategy_gold_silver"]
                else:
                    stock_data_context["strategy_gold_silver"] = None
                
                # C. 獲取可轉債數據 (需要日線現價來計算乖離率)
                if "close" in stock_data_context:
                    current_price = stock_data_context["close"]
                    cb_data = get_cb_info(ticker, current_price)
                    if cb_data:
                        stock_data_context.update(cb_data) # 合併 has_cb, cb_list
                    else:
                        stock_data_context["has_cb"] = False
                        stock_data_context["cb_list"] = []
                
                app.logger.info("Stock data fetched and merged successfully.")

            except Exception as e:
                app.logger.error(f"Failed to fetch stock data: {e}")
                # 即使抓取失敗，程式仍繼續執行，讓 AI 根據有限資訊或網路搜尋回答
        
        # --- 步驟 2: 構建 Prompt ---
        # 讀取 System Prompt (優先使用 Payload，否則讀取檔案)
        final_system_prompt = ""
        if system_prompt:
            final_system_prompt = system_prompt
        else:
            file_content, error = read_prompt_file()
            if error:
                app.logger.warning(error)
                final_system_prompt = "你是專業的投資分析師，請依據數據進行分析。"
            else:
                final_system_prompt = file_content
        
        # 將合併後的數據轉為 JSON 字串
        json_input_str = json.dumps(stock_data_context, ensure_ascii=False, indent=2)
        
        # 構建最終給 Gemini 的輸入內容 (User Prompt)
        # 明確標示這是系統自動獲取的 JSON 數據
        final_user_input = f"""
{user_question}

---
### 系統自動獲取數據 (JSON)
請嚴格依據以下數據進行技術分析與策略判斷：
```json
{json_input_str}
```
"""

        # --- 步驟 3: 初始化 Gemini Client ---
        app.logger.info(f"Initializing Gemini Client...")
        client = genai.Client(
            vertexai=True, 
            project=PROJECT_ID,
            location=LOCATION
        )

        # 啟用 Google Search 工具 (對應 Prompt 的基本面聯網要求)
        search_tool = Tool(
            google_search=GoogleSearch() 
        )

        # --- 步驟 4: 生成內容 ---
        app.logger.info("Calling Gemini API...")
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=final_user_input,
            config=GenerateContentConfig(
                tools=[search_tool],
                system_instruction=final_system_prompt,
                temperature=0.3, # 降低隨機性，讓分析更穩定
            )
        )
        
        answer = response.text if response.text else "抱歉，分析生成失敗，請稍後再試。"
        app.logger.info("Gemini response received.")

        return jsonify({"answer": answer})

    except Exception as e:
        app.logger.error(f"Task Execution Error: {e}")
        return jsonify({"error": str(e)}), 500

# 回溯相容或舊路徑轉發 (如果需要)
@app.route('/', methods=['POST'])
def root_endpoint():
    return execute_task()

# -------------------------------------------------------
# 本機測試區塊
# -------------------------------------------------------
if __name__ == "__main__":
    print("=== Flask App 本機啟動測試 ===")
    app.run(host='0.0.0.0', port=8080, debug=True)
