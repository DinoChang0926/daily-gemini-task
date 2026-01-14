# 📈 Gemini 股票自動分析助理 (Gemini Stock Analyst - Sara Morphology)

這是一個全自動化的股票投資分析系統。透過 Google Sheets 管理持股，結合 Google Cloud Run 與 Gemini 2.0 Flash (Vertex AI)，實現「即時聯網查價」與「莎拉型態學 (Sara Morphology)」策略分析，並將專業的 HTML 分析週報自動寄送至您的信箱。

## 🚀 核心功能 (Key Features)

自動化代號補全：只需輸入股票名稱（如「廣達」），系統自動透過 AI 查詢並填入股票代號。

即時聯網落地 (Grounding)：整合 Google Search Tool，AI 自動檢索最新的即時股價、EPS、營收 YoY 與均線數據，拒絕幻覺。

Serverless 架構：前端使用 GAS，後端使用 Cloud Run，低成本且高擴充性。

動態 Prompt 管理：策略邏輯儲存於 Google Doc，無需更動程式碼即可調整 AI 分析風格。

## 🏗️ 系統架構 (Architecture)

本專案採用前後端分離架構，利用 Google 生態系優勢進行串接。
```mermaid
graph TD
    User[使用者] -->|輸入股票/成本| Sheet[Google Sheets (資料庫/UI)]
    
    subgraph Frontend [Google Apps Script]
        Menu[自訂選單] -->|觸發| Main[主控制器]
        Main -->|1. 檢查代號| AutoFill[自動補全模組]
        Main -->|2. 讀取 Prompt| Doc[Google Doc (Prompt)]
        Main -->|3. 發送請求| API_Call[UrlFetchApp]
        API_Call -->|4. 接收回應| Formatter[HTML 渲染器]
        Formatter -->|5. 寄信| Gmail[Gmail Service]
    end
    
    subgraph Backend [Google Cloud Run]
        Flask[Flask Server] -->|身份驗證| Auth[Auth Layer]
        Auth -->|掛載工具| Tool[Google Search Tool]
        Tool -->|推理分析| Vertex[Vertex AI (Gemini 2.0)]
    end
    
    subgraph External [外部資源]
        Vertex <-->|聯網搜尋| GoogleSearch[Google Search Engine]
    end

    Sheet <--> Frontend
    Frontend <-->|HTTPS POST| Backend
```

## 🛠️ 技術棧 (Tech Stack)

Frontend: Google Sheets, Google Apps Script (GAS)

Backend: Python 3.10+, Flask, Gunicorn

AI Model: Gemini 2.0 Flash (via Vertex AI SDK)

Hosting: Google Cloud Run (Region: us-central1)

Tools: Google Search Grounding

## 📂 目錄結構 (Directory Structure)
```
.
├── backend/                  # Python 後端程式碼
│   ├── main.py               # Flask 主程式 (含 Gemini 呼叫邏輯)
│   ├── requirements.txt      # Python 依賴套件
│   └── Procfile              # Cloud Run 啟動指令
├── gas/                      # Google Apps Script 前端代碼
│   └── Code.gs               # GAS 主邏輯
├── prompt/                   # 策略提示詞備份
│   └── system_prompt.txt     # (請將此內容複製到 Google Doc)
└── cloudbuild.yaml           # CI/CD 部署設定 (GitHub Trigger)
```

## ⚙️ 部署教學 (Deployment)

### 步驟 1：部署後端 (Google Cloud Run)

確認已安裝 Google Cloud SDK 並啟用專案。

建立 requirements.txt：

flask
gunicorn
functions-framework
python-dotenv
google-genai
google-cloud-aiplatform


建立 Procfile：

web: functions-framework --target=execute_gemini_task --port=8080


進入後端目錄並部署 (關鍵步驟)：

由於程式碼位於 backend 資料夾，請先進入該目錄：

cd backend


接著部署至 Cloud Run (務必選擇 us-central1 以支援 Search Tool)：

gcloud run deploy daily-gemini-task \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GCP_PROJECT_ID=你的專案ID,MODEL_NAME=gemini-2.0-flash-001,API_SECRET=你的自訂密鑰


記下 Cloud Run 產生的 URL (結尾通常是 .run.app)。

### 步驟 2：設定策略 Prompt

在 Google Drive 建立一個 Google Doc。

將 Prompt 內容 貼入檔案中。

記下該 Google Doc 的 File ID (網址 d/ 後面那串)。

### 步驟 3：設定前端 (Google Apps Script)

開啟 Google Sheet -> 擴充功能 -> Apps Script。

複製 gas/Code.gs 的內容貼入編輯器。

### 修改全域變數設定：

const API_URL = "[https://你的-cloud-run-url.a.run.app/execute_gemini_task](https://你的-cloud-run-url.a.run.app/execute_gemini_task)";
const API_KEY = "你的自訂密鑰"; // 需與 Python 環境變數一致
const PROMPT_FILE_ID = "你的_Google_Doc_ID";


儲存並重新整理 Google Sheet。

## 📖 使用說明 (Usage)

### 1. 準備表格資料

請確保 Google Sheet 的欄位順序如下：

欄位位置

欄位名稱

說明

A2

Email

接收報告的電子信箱

A5

狀態

程式會自動更新執行進度

B 欄

股票名稱

輸入中文名稱 (例：廣達)

C 欄

股票代號

留空即可，程式會自動補全

D 欄

成本價

輸入持有成本 (若無則輸入 0 或空)

### 2. 執行功能

#### 手動觸發

點選 Google Sheet 上方出現的 「Gemini AI」 選單：

1. 自動填入股票代號：掃描 B 欄，若 C 欄為空，自動呼叫 AI 查詢代號並填入。

2. 執行投資組合分析：讀取清單，進行聯網分析，並寄送 Email。

#### 設定排程自動執行 (Automation)

若希望每天定時收到分析報告，請在 Apps Script 中設定觸發條件：

在 GAS 編輯器左側選單點擊 「觸發條件 (鬧鐘圖示)」。

點擊右下角 「新增觸發條件」。

設定如下：

執行功能：analyzeAllSheets

部署作業：前端 (Head)

事件來源：時間驅動

時間類型：日

時間：選擇您希望執行時段 (例如：上午 8 點 到 9 點)

儲存後，系統即會每日自動執行分析並寄信。

📝 License

This project is licensed under the MIT License.