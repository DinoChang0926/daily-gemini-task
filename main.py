from flask import jsonify
import functions_framework
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
from google.genai.types import GenerateContentConfig, Tool, GoogleSearch 

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
        file_path = os.path.join(base_dir, 'prompt.txt')
        
        if not os.path.exists(file_path):
            return None, "錯誤: 找不到 prompt.txt 檔案"
            
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read(), None
    except Exception as e:
        return None, f"讀取 Prompt 發生錯誤: {str(e)}"

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
        secret = data.get("secret", "")
        # 2. 驗證密鑰
        if str(secret) != str(API_SECRET): # 轉字串比對較保險
            return jsonify({"error": "Unauthorized"}), 403
            
        if not user_question:
            return jsonify({"error": "Question is empty"}), 400

        # 3. 組合 Prompt
        # <--- 修正 2: 處理 tuple 回傳值
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

        # 4. 初始化 Client
        client = genai.Client(
            vertexai=True, 
            project=PROJECT_ID,
            location=LOCATION
        )

        # 5. 設定 Google 搜尋工具
        search_tool = Tool(
            google_search=GoogleSearch() 
        )

        # 6. 呼叫 Gemini (啟用 Search)
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=user_question,
            config=GenerateContentConfig(
                tools=[search_tool],
                system_instruction=final_system_prompt,
                temperature=0.3,
            )
        )

        return jsonify({"answer": response.text})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

# -------------------------------------------------------
# 本機測試區塊
# -------------------------------------------------------
if __name__ == "__main__":
    print("=== 開始本機測試 ===")     
  
    # 模擬 Flask 的 request 物件
    class MockRequest:
        def get_json(self, silent=True):
            return {
                "question": "請幫我分析廣達 (2382) 的現況", 
                "secret": API_SECRET 
            }

    print("\n[測試] 模擬呼叫:")
    # 這裡把 MockRequest 傳進去
    result = execute_gemini_task(MockRequest())
    
    # 這裡回傳的是 tuple (response_body, status_code) 或是 response 物件
    # 為了在本機看到結果，我們簡單處理一下
    try:
        print(result.get_data(as_text=True))
    except:
        print(result)
    
    print("\n=== 測試結束 ===")