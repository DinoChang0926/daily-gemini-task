# 📈 Gemini 股票自動分析助理 (Gemini Stock Analyst - Sara Morphology)

這是一個全自動化的股票投資分析系統。透過 Google Sheets 管理持股，結合 Google Cloud Run 與 Gemini 2.0 Flash (Vertex AI)，實現「即時聯網查價」與「基本面、技術線形」策略分析，並將專業的 HTML 分析自動寄送至您的信箱。

## 🚀 核心功能 (Key Features)

* 企業級資安 (Enterprise Security)：導入 Firebase Auth 與 API Gateway，徹底封鎖後端 IP，僅允許持有有效 Token 的流量進入。
* 自動化代號補全：只需輸入股票名稱（如「廣達」），系統自動透過 AI 查詢並填入股票代號。
* 即時聯網落地 (Grounding)：整合 Google Search Tool，AI 自動檢索最新的即時股價、EPS、營收 YoY 與均線數據，拒絕幻覺。
* Serverless 架構：前端使用 GAS，後端使用 Cloud Run，低成本且高擴充性。
* 動態 Prompt 管理：策略邏輯儲存於 Google Doc，無需更動程式碼即可調整 AI 分析風格。

## 🏗️ 系統架構 (Architecture)

本專案採用前後端分離架構，利用 Google 生態系優勢進行串接。

```mermaid
graph TD
    User[使用者] -->|輸入股票/成本| Sheet["Google Sheets (UI)"]
    
    subgraph Frontend [Google Apps Script]
        GAS[GAS Client] <-->|1. 登入換證| Firebase[Firebase Auth]
        GAS -->|2. 攜帶 JWT Token| Gateway[GCP API Gateway]
    end
    
    subgraph Security Layer [Google Cloud Platform]
        Gateway -->|3. 驗證 Token & 轉發| CloudRun[Cloud Run Service]
    end
    
    subgraph Backend [Python Flask]
        CloudRun -->|身份驗證| Auth[Secret Check]
        Auth -->|掛載工具| Tool[Google Search Tool]
        Tool -->|推理分析| Vertex["Vertex AI (Gemini 2.0)"]
    end
    
    subgraph External [外部資源]
        Vertex <-->|聯網搜尋| GoogleSearch[Google Search Engine]
    end
```

## 🛠️ 技術棧 (Tech Stack)

Frontend: Google Sheets, Google Apps Script (GAS)

Security: Firebase Authentication, Google Cloud API Gateway

Backend: Python 3.10+, Flask, Gunicorn

AI Model: Gemini 2.0 Flash (via Vertex AI SDK)

Hosting: Google Cloud Run (Region: us-central1)

## 📂 目錄結構 (Directory Structure)
```
.
├── backend/                  # Python 後端程式碼
│   ├── main.py               # Flask 主程式 (含 Gemini 呼叫邏輯)
│   ├── requirements.txt      # Python 依賴套件
│   └── Procfile              # Cloud Run 啟動指令
├── gas/                      # Google Apps Script 前端代碼
│   └── Code.gs               # GAS 主邏輯 (含 Firebase 登入模組)
├── prompt/                   # 策略提示詞備份
│   └── system_prompt.txt     # (請將此內容複製到 Google Doc)
├── openapi2-run.yaml         # [新增] API Gateway 設定檔
└── cloudbuild.yaml           # CI/CD 部署設定
```

## ⚙️ 部署教學 (Deployment)

### 步驟 1：部署後端 (Google Cloud Run)

進入 backend 目錄並部署至 Cloud Run (需記下 URL，後續設定 Gateway 會用到)。

```
cd backend
gcloud run deploy daily-gemini-task \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GCP_PROJECT_ID=你的專案ID,MODEL_NAME=gemini-2.0-flash-001
```


### 步驟 2：建立安全層 (Gateway & Firebase)

* 啟用 API：啟用 API Gateway, Service Control, Service Management API。

* Firebase 設定：
    * 在 Firebase Console 建立專案。
    * 啟用 Authentication (Email/Password)。
    * 建立一個測試用帳號 (Email/Password)。
    * 取得 Web API Key。

* 設定 Gateway：
    * 修改 openapi2-run.yaml，填入 Project ID、Cloud Run URL、Firebase Issuer/Audience。
    * 執行指令建立 API Config 與 Gateway。

### 步驟 3：封鎖後門 (Lockdown)

Gateway 建立成功後，移除 Cloud Run 的公開存取權限，僅允許 Gateway 的 Service Account 呼叫。

### 步驟 4：設定策略 Prompt
* 在 Google Drive 建立一個 Google Doc。
* 將 prompt/system_prompt.txt 內容貼入檔案中。
* 記下該 Google Doc 的 File ID (網址 d/ 後面那串)。



### 步驟 5：設定前端 (Google Apps Script)

```
// ==========================================
// 1. 全域設定區
// ==========================================
const GATEWAY_URL = "[https://你的-gateway-url.gateway.dev/task](https://你的-gateway-url.gateway.dev/task)"; // 注意：這是 Gateway 網址

// Firebase 設定 (用於獲取 Token)
const FIREBASE_API_KEY = "你的_Firebase_Web_API_Key";
const FIREBASE_EMAIL = "test@example.com";
const FIREBASE_PASSWORD = "你的密碼";
const PROMPT_FILE_ID = "你的_Google_Doc_ID"; 
```

## 📖 使用說明 (Usage)

### 1. 準備表格資料

| 欄位   |   名稱      |  說明                       |
| ----- | --------    | --------                    |
| A2    | Email       | 接收報告的電子信箱            |
| A5   | 狀態        | 狀態(程式會自動更新執行進度)   |
| B     | 股票名稱     | 例如：廣達                   |
| C     | 股票代號     | 可留空，系統自動補全          |
| D     | 成本價       | 持有成本 (可選)              |


### 2. 執行功能

點選上方選單 「Gemini AI」：

* 自動填入股票代號：系統會自動登入 Firebase 取得 Token，通過 Gateway 查詢代號。

* 執行投資組合分析：觸發完整分析流程，產生 HTML 報告並寄信。

### 3. 自動化排程

在 Apps Script 設定「時間驅動」觸發器 (例如每日上午 9 點)，即可每日定時自動執行分析。

## 📝 License

This project is licensed under the MIT License.
