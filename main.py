import functions_framework
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

# 1. 載入環境變數
load_dotenv(override=True)
PROJECT_ID = "storied-phalanx-239007"
LOCATION = "us-central1"
# 注意：Vertex AI 模式其實不需要讀取 API Key，但保留這行沒關係
MODEL = os.environ.get("MODEL_NAME", "gemini-1.5-flash") 
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
def execute_gemini_task(request):
    try:
        request_json = request.get_json(silent=True)
        
        # 1. 安全檢查 (Secret 驗證)
        if API_SECRET:
            input_secret = request_json.get('secret') if request_json else None
            if input_secret != API_SECRET:
                return {"error": "權限不足 (Unauthorized)"}, 403

        # [已移除] 檢查 GENAI_API_KEY 的段落
        # 因為 Vertex AI 是認 IAM 權限，不認 API Key，所以那段檢查可以拿掉。

        # 2. 決定 System Prompt
        system_instruction = ""
        
        if request_json and 'system_prompt' in request_json:
            system_instruction = request_json['system_prompt']
        else:
            file_content, error = read_prompt_file()
            if error:
                return {"error": error}, 500
            system_instruction = file_content

        # 3. 取得問題
        if request_json and 'question' in request_json:
            user_question = request_json['question']
        else:
            return {"error": "請提供 question 參數"}, 400

        # 4. 呼叫 Gemini (Vertex AI 模式)
        # 這裡的縮排必須正確
        client = genai.Client(
            vertexai=True, 
            project=PROJECT_ID, 
            location=LOCATION
        )
        
        final_prompt = f"{system_instruction}\n\n[使用者提問]\n{user_question}"

        response = client.models.generate_content(
            model=MODEL, 
            contents=final_prompt
        )

        return {
            "answer": response.text
        }, 200

    except Exception as e:
        return {"error": f"執行失敗: {str(e)}"}, 500

# -------------------------------------------------------
# 本機測試區塊
# -------------------------------------------------------
if __name__ == "__main__":
    print("=== 開始本機測試 ===")     
  
    class MockRequestCustom:
        def get_json(self, silent=True):
            # 這裡模擬傳入 Secret (如果有設的話)
            return {
                "question": "請幫我分析廣達", 
                "secret": os.environ.get("API_SECRET")
            }

    print("\n[測試 2] 使用自訂問題:")
    # 這裡只印出結果，不印狀態碼
    result = execute_gemini_task(MockRequestCustom())
    print(result)
    
    print("\n=== 測試結束 ===")