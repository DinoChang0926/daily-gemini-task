from flask import jsonify
import functions_framework
import os
import re
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv
from google.genai.types import GenerateContentConfig, Tool, GoogleSearch 
from stock_analysis import get_precise_data  
from ticker_utils import get_ticker_by_name

# 1. 載入環境變數
load_dotenv(override=True)
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "storied-phalanx-239007") # 建議統一讀 .env
LOCATION = "us-central1"
MODEL_NAME = os.environ.get("MODEL_NAME", "gemini-2.0-flash-001") 
API_SECRET = os.environ.get("API_SECRET")

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

@functions_framework.http
def get_stock_data(request):
    """
    獨立的 API 端點，供外部直接查詢股票數據
    Method: POST
    Payload: { "ticker": "2382" }
    """
    try:
        data = request.get_json(silent=True)
        if not data or "ticker" not in data:
            return jsonify({"error": "Missing 'ticker' in payload"}), 400
            
        ticker = data.get("ticker", "")
        # 直接呼叫函式獲取資料
        stock_info = get_precise_data(ticker)
        
        return jsonify(stock_info)
    except Exception as e:
         return jsonify({"error": str(e)}), 500

@functions_framework.http
def get_ticker_code(request):
    """
    透過股票名稱查詢代碼的 API 端點
    Method: POST
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

@functions_framework.http
def execute_gemini_task(request):  # <--- 修正 1: 這裡必須有 request 參數
    try:
        # 1. 接收資料
        # 使用 request.get_json() 比較安全
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Empty payload"}), 400

        user_question = data.get("question", "")
        system_prompt = data.get("system_prompt", "")
            
        if not user_question:
            return jsonify({"error": "Question is empty"}), 400

        # --- Pre-fetch 策略: 自動偵測股票代號並注入資料 ---
        # 簡單的正則表達式: 抓取 4 位數字 (台股代號)
        stock_context = ""
        match = re.search(r'(\d{4})', user_question)
        if match:
            ticker = match.group(1)
            print(f"Detected Ticker: {ticker}, fetching data...")
            try:
                # 直接呼叫 Python 函式 (RAG 模式)
                data_json = get_precise_data(ticker)
                
                # 將數據轉為 JSON 字串，加入到 Prompt 上下文中
                stock_context = f"\n\n[系統自動獲取的即時股市數據]\n```json\n{json.dumps(data_json, ensure_ascii=False, indent=2)}\n```\n請根據上述數據進行分析。"
                print("Stock data injected successfully.")
            except Exception as e:
                print(f"Warning: Failed to fetch stock data: {e}")
                # 即使抓不到資料，也繼續執行，讓 AI 嘗試聯網
        
        # 2. 組合 Prompt
        final_system_prompt = ""
        if system_prompt:
            final_system_prompt = system_prompt
        else:
            file_content, error = read_prompt_file()
            if error:
                print(f"Warning: {error}") # 印出警告但不中斷
                final_system_prompt = "你是專業的投資分析師。" # 給個預設值以防萬一
            else:
                final_system_prompt = file_content
        
        # 將注入的資料附加到 System Prompt 或 User Prompt 尾端
        # 這裡選擇附加到 User Question 後方，讓 AI 就像看到一份包含數據的報告
        final_user_input = user_question + stock_context

        # 4. 初始化 Client
        client = genai.Client(
            vertexai=True, 
            project=PROJECT_ID,
            location=LOCATION
        )

        # 5. 設定 Google 搜尋工具
        # 回歸最單純的設定：只給 Google Search，因為數據已經透過 RAG 餵給它了
        search_tool = Tool(
            google_search=GoogleSearch() 
        )

        # 6. 呼叫 Gemini (啟用 Search)
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=final_user_input,
            config=GenerateContentConfig(
                tools=[search_tool],
                system_instruction=final_system_prompt,
                temperature=0.3,
            )
        )

        return jsonify({"answer": response.text})

    except Exception as e:
        print(f"Error Details: {e}") # Print full string representation
        if hasattr(e, 'message'):
             print(f"Error Message: {e.message}")
        return jsonify({"error": str(e)}), 500

# -------------------------------------------------------
# 本機測試區塊
# -------------------------------------------------------
if __name__ == "__main__":
    print("=== 開始本機測試 ===")     
    from flask import Flask
    app = Flask(__name__)

    # 模擬 Flask 的 request 物件
    class MockRequest:
        def get_json(self, silent=True):
            return {
                "question": "請幫我分析廣達 (2382) 的現況", 
                "secret": API_SECRET 
            }

    print("\n[測試 1] 測試 get_stock_data API:")
    class MockStockRequest:
        def get_json(self, silent=True):
            return {"ticker": "2382"}
            
    with app.app_context():
        stock_result = get_stock_data(MockStockRequest())
        try:
             print(stock_result.get_data(as_text=True))
        except:
             print(stock_result)

    print("\n[測試 2] 測試 execute_gemini_task (含 Pre-fetch):")
    # 模擬 Flask 的 request 物件
    class MockAgentRequest:
        def get_json(self, silent=True):
            return {
                "question": "請幫我分析廣達 (2382) 的現況",  # 這裡包含 2382，應該觸發 Pre-fetch
                "secret": API_SECRET 
            }
    
    with app.app_context():
        # 這裡把 MockRequest 傳進去
        result = execute_gemini_task(MockAgentRequest())
        
        # 這裡回傳的是 tuple (response_body, status_code) 或是 response 物件
        # 為了在本機看到結果，我們簡單處理一下
        try:
            # jsonify 回傳的是 Response 物件
            print(result.get_data(as_text=True))
        except:
            print(result)
    
    print("\n[測試 3] 測試 get_ticker_code API:")
    class MockTickerRequest:
        def get_json(self, silent=True):
            return {"name": "廣達"}
            
    with app.app_context():
        ticker_result = get_ticker_code(MockTickerRequest())
        try:
             print(ticker_result.get_data(as_text=True))
        except:
             print(ticker_result)

    print("\n=== 測試結束 ===")