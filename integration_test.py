
import sys
import os
import json

# Add backend directory to sys.path to import modules
sys.path.append(os.path.join(os.getcwd(), 'backend'))

import requests
import time

def run_test():
    with open('test.json', 'r', encoding='utf-8') as f:
        test_data = json.load(f)
    
    stock_ids = test_data.get("stock_id", [])
    url = "http://localhost:8080/task"
    
    print(f"Starting End-to-End Agent Test for {len(stock_ids)} stocks...")
    print(f"Target URL: {url}")
    print("="*60)

    for ticker in stock_ids:
        print(f"🤖 User asking about: {ticker}...")
        payload = {
            "question": f"請幫我分析 {ticker} 的股票，特別是 60分K 的部分。",
            # system_prompt 讓後端讀取預設的 prompt.txt 即可，不需額外傳
        }
        
        try:
            start_time = time.time()
            # 增加 Timeout 到 300 秒，避免 Gemini 思考過久導致連線中斷
            response = requests.post(url, json=payload, timeout=300) 
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                answer = data.get("answer", "No answer provided")
                
                print(f"✅ Response received in {duration:.2f}s")
                print("-" * 20 + " AI Analysis " + "-" * 20)
                # 只印出前 500 字摘要，避免洗版
                print(answer[:500] + "...\n(略)")
                print("-" * 60)
            else:
                print(f"❌ Error {response.status_code}: {response.text}")

        except Exception as e:
            print(f"❌ Request Failed: {e}")
        
        print("\n")

if __name__ == "__main__":
    run_test()
