import functions_framework
import os
import google.generativeai as genai

# 從環境變數讀取 API Key
GENAI_API_KEY = os.environ.get("GOOGLE_API_KEY")

@functions_framework.http
def execute_gemini_task(request):
    try:
        # 1. 設定 API Key
        genai.configure(api_key=GENAI_API_KEY)

        # 2. 設定模型 (使用免費的 Flash 模型)
        model = genai.GenerativeModel("gemini-1.5-flash")

        # 3. 你的 Prompt 邏輯 (這裡放入你想自動化的指令)
        # 範例：每天分析某個固定的資料或生成一段日報
        prompt = """
        你是一個資深的 C# 技術顧問。
        請提供一個今天值得學習的 C# .NET 8 優化技巧，
        並附上簡短的程式碼範例。
        """

        # 4. 執行生成
        response = model.generate_content(prompt)
        result_text = response.text

        # 5. (未來擴充) 這裡可以寫程式把 result_text 寄到你的 Email 或存入資料庫
        print(f"執行成功: {result_text}") # 這會出現在 GCP Logs

        return f"Gemini 執行完成！結果已寫入 Log。\n摘要: {result_text[:50]}...", 200

    except Exception as e:
        return f"發生錯誤: {str(e)}", 500