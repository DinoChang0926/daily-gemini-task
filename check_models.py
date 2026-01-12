import os
from google import genai
from dotenv import load_dotenv

load_dotenv(override=True)

API_KEY = os.environ.get("GOOGLE_API_KEY")

if not API_KEY:
    print("錯誤：找不到 API Key")
else:
    print(f"正在使用 Key: {API_KEY[:5]}... 查詢可用模型")
    try:
        client = genai.Client(api_key=API_KEY)
        # 列出所有模型
        print("--- 可用模型清單 ---")
        for m in client.models.list():
            # 過濾出包含 gemini 的模型以方便閱讀
            if "gemini" in m.name:
                print(f"名稱: {m.name}")
                
    except Exception as e:
        print(f"查詢失敗: {e}")