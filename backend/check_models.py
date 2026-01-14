from google import genai
from dotenv import load_dotenv
import os

load_dotenv(override=True)

# 1. 連線 (使用 us-central1 最穩，因為模型最全)
# 如果 us-central1 跑出結果，我們就改用 us-central1
TARGET_LOCATION = "us-central1" 

client = genai.Client(
    vertexai=True, 
    project="storied-phalanx-239007", 
    location=TARGET_LOCATION
)

print(f"======== 正在掃描 {TARGET_LOCATION} 所有可用模型 ========")

try:
    # 直接列出所有模型 (不加 config，避免報錯)
    for model in client.models.list():
        # model.name 是完整的資源路徑，我們只看最後一段
        # 例如: publishers/google/models/gemini-1.5-flash-002
        full_name = model.name
        short_name = full_name.split('/')[-1]
        
        # 只印出跟 gemini 有關的
        if "gemini" in short_name.lower():
            print(f"✅ 發現: {short_name}")

except Exception as e:
    print(f"❌ 掃描失敗: {e}")

print("==================================================")