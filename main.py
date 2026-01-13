import functions_framework
import os
from google import genai
from dotenv import load_dotenv

# 1. 載入環境變數 (強制覆寫，確保讀取到最新的 .env)
load_dotenv(override=True)

# 取得 API Key
GENAI_API_KEY = os.environ.get("GOOGLE_API_KEY")
MODEL= os.environ.get("MODEL_NAME", "gemini-flash-latest")
API_SECRET = os.environ.get("API_SECRET")  # 可選的安全密鑰

def read_prompt_file():
    """
    讀取同目錄下的 prompt.txt 檔案內容作為 System Instruction
    使用絕對路徑以確保在 Cloud Functions 環境下能正確找到檔案
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
        
        # 1. 安全檢查
        if API_SECRET:
            input_secret = request_json.get('secret') if request_json else None
            if input_secret != API_SECRET:
                return {"error": "權限不足 (Unauthorized)"}, 403

        if not GENAI_API_KEY:
            return {"error": "未設定 GOOGLE_API_KEY"}, 500

        # 2. 決定 System Prompt (核心修改)
        # 優先使用 GAS 傳過來的 prompt，如果沒有則使用預設值
        if request_json and 'system_prompt' in request_json:
            system_instruction = request_json['system_prompt']
        else:
            system_instruction = read_prompt_file()

        # 3. 取得問題
        if request_json and 'question' in request_json:
            user_question = request_json['question']
        else:
            return {"error": "請提供 question 參數"}, 400

        # 4. 呼叫 Gemini
        client = genai.Client(api_key=GENAI_API_KEY)
        
        final_prompt = f"{system_instruction}\n\n[使用者提問]\n{user_question}"

        response = client.models.generate_content(
            model=MODEL, 
            contents=final_prompt
        )

        return {
            "answer": response.text
        }, 200

    except Exception as e:
        return {"error": str(e)}, 500

# -------------------------------------------------------
# 本機測試區塊 (Local Testing)
# -------------------------------------------------------
if __name__ == "__main__":
    print("=== 開始本機測試 ===")     
  
    class MockRequestCustom:
        def get_json(self, silent=True):
            return {"question": "請幫我分析廣達"}

    print("\n[測試 2] 使用自訂問題:")
    print(execute_gemini_task(MockRequestCustom())[0])
    
    print("\n=== 測試結束 ===")