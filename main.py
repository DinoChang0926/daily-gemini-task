import functions_framework
import os
from google import genai
from google.genai import types # 引入 types 以便更精確控制設定
from dotenv import load_dotenv

# 1. 載入環境變數
load_dotenv(override=True)

GENAI_API_KEY = os.environ.get("GOOGLE_API_KEY")
# 建議改用明確的模型名稱，新版 SDK 對別名支援較嚴格
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
        
        # 1. 安全檢查
        if API_SECRET:
            input_secret = request_json.get('secret') if request_json else None
            if input_secret != API_SECRET:
                return {"error": "權限不足 (Unauthorized)"}, 403

        if not GENAI_API_KEY:
            return {"error": "未設定 GOOGLE_API_KEY"}, 500

        # 2. 決定 System Prompt (修正 Tuple 解包錯誤)
        system_instruction = ""
        
        if request_json and 'system_prompt' in request_json:
            system_instruction = request_json['system_prompt']
        else:
            # 【關鍵修正】這裡必須解包 (Unpack) 兩個回傳值
            file_content, error = read_prompt_file()
            if error:
                # 若讀取失敗，視需求決定報錯或降級，這裡選擇回傳錯誤
                return {"error": error}, 500
            system_instruction = file_content

        # 3. 取得問題
        if request_json and 'question' in request_json:
            user_question = request_json['question']
        else:
            return {"error": "請提供 question 參數"}, 400

        # 4. 呼叫 Gemini (使用新版 SDK 寫法)
        client = genai.Client(api_key=GENAI_API_KEY)
        
        # 組合 Prompt
        final_prompt = f"{system_instruction}\n\n[使用者提問]\n{user_question}"

        response = client.models.generate_content(
            model=MODEL, 
            contents=final_prompt
        )

        return {
            "answer": response.text
        }, 200

    except Exception as e:
        # 這裡會捕捉執行期間的錯誤，但無法捕捉 Import 錯誤
        return {"error": f"執行失敗: {str(e)}"}, 500

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