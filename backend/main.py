import os
import re
import json
from flask import Flask, request, jsonify
from google import genai
from google.genai import types
from dotenv import load_dotenv
from google.genai.types import GenerateContentConfig, Tool, GoogleSearch 
from stock_analysis import get_precise_data  
from ticker_utils import get_ticker_by_name

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
    # 隨便查一個，觸發 cache 下載
    get_ticker_by_name("台積電")
    print("Stock cache warmed up successfully.")
except Exception as e:
    print(f"Warning: Cache warming failed: {e}")

# 綁定 Gunicorn Logger (確保 Cloud Run 能看到日誌)
import logging
gunicorn_logger = logging.getLogger('gunicorn.error')
app.logger.handlers = gunicorn_logger.handlers
app.logger.setLevel(gunicorn_logger.level)

# 應用程式啟動時預熱快取
print("Warming up stock cache...")
try:
    # 隨便查一個，觸發 cache 下載
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
    核心 Gemini 分析任務端點
    """
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Empty payload"}), 400

        user_question = data.get("question", "")
        system_prompt = data.get("system_prompt", "")
            
        if not user_question:
            return jsonify({"error": "Question is empty"}), 400

        # --- Pre-fetch 策略: 自動偵測股票代號並注入資料 ---
        stock_context = ""
        match = re.search(r'(\d{4})', user_question)
        if match:
            ticker = match.group(1)
            print(f"Detected Ticker: {ticker}, fetching data...")
            try:
                data_json = get_precise_data(ticker)
                stock_context = f"\n\n[系統自動獲取的即時股市數據]\n```json\n{json.dumps(data_json, ensure_ascii=False, indent=2)}\n```\n請根據上述數據進行分析。"
                print("Stock data injected successfully.")
            except Exception as e:
                print(f"Warning: Failed to fetch stock data: {e}")
        
        # 2. 組合 Prompt
        final_system_prompt = ""
        if system_prompt:
            final_system_prompt = system_prompt
        else:
            file_content, error = read_prompt_file()
            if error:
                print(f"Warning: {error}")
                final_system_prompt = "你是專業的投資分析師。"
            else:
                final_system_prompt = file_content
        
        final_user_input = user_question + stock_context

        # 4. 初始化 Client
        print(f"Initializing Gemini Client for question: {user_question[:30]}...")
        client = genai.Client(
            vertexai=True, 
            project=PROJECT_ID,
            location=LOCATION
        )

        search_tool = Tool(
            google_search=GoogleSearch() 
        )

        # 6. 呼叫 Gemini
        print("Waiting for Gemini response (with Google Search)...")
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=final_user_input,
            config=GenerateContentConfig(
                tools=[search_tool],
                system_instruction=final_system_prompt,
                temperature=0.3,
            )
        )
        print("Gemini response received.")

        return jsonify({"answer": response.text})

    except Exception as e:
        print(f"Error Details: {e}")
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
