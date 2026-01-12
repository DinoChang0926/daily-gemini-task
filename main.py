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
    """
    GCP Cloud Function 主進入點
    """
    try:
        # 檢查 API Key
        if not GENAI_API_KEY:
            return "錯誤: 未設定 GOOGLE_API_KEY 環境變數", 500
        
        request_json = request.get_json(silent=True)
        
        if API_SECRET:
            # 從 JSON 拿密碼，如果沒有就拿 header (雙重保險)
            input_secret = request_json.get('secret') if request_json else None
            
            if input_secret != API_SECRET:
                print(f"安全警告: 收到錯誤的密鑰 - {input_secret}")
                return {"error": "權限不足 (Unauthorized)"}, 403

        # 初始化 Client
        client = genai.Client(api_key=GENAI_API_KEY)

        # 讀取系統人設 (System Prompt)
        system_instruction, error_msg = read_prompt_file()
        if error_msg:
            return error_msg, 500

        # 解析使用者提問 (User Prompt)
        # 優先從 HTTP POST JSON Body 取得 'question' 欄位
        # 若無傳入，則使用預設問題
        request_json = request.get_json(silent=True)
        
        if request_json and 'question' in request_json:
            user_question = request_json['question']
            source = "HTTP 請求參數"
        else:
            user_question = "請簡介 C# .NET 9 的其中一個新特性並附上範例。"
            source = "預設腳本"

        # 組合最終 Prompt
        final_prompt = f"{system_instruction}\n\n[使用者提問]\n{user_question}"

        print(f"--- 執行資訊 ---\n來源: {source}\n問題: {user_question}\n----------------")

        # 呼叫 Gemini API
        # 建議先使用 1.5-flash 確保穩定，若要用 2.5 請改為 'gemini-2.5-flash'
        response = client.models.generate_content(
            model=MODEL, 
            contents=final_prompt
        )

        result_text = response.text
        print(f"執行成功，回應長度: {len(result_text)}")
        
        return {
            "answer": result_text,
            "source": "Gemini API"
        }, 200

    except Exception as e:
        print(f"執行發生例外狀況: {e}")
        return f"發生錯誤: {str(e)}", 500

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