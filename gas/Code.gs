// ==========================================
// 1. 全域設定區 (請務必填寫)
// ==========================================
const GATEWAY_URL = "https://daily-gemini-task-gateway-y87h38t.us-central1.gateway.dev"; 
const API_URL = "";
const PROMPT_FILE_ID = ""; // google doc
const FIREBASE_API_KEY = ""; // 填入 Web API Key
const FIREBASE_EMAIL = ""; // 填入測試帳號
const FIREBASE_PASSWORD = "";   // 填入測試密碼
// ==========================================
// 2. 選單與主控制器
// ==========================================

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Gemini AI')
    .addItem('1. 自動填入股票代號', 'autoFillTickers')
    .addItem('2. 執行投資組合分析', 'analyzeAllSheets')
    .addToUi();
}

/**
 * 功能 1: 自動填寫 C 欄代號
 */
function autoFillTickers() {
  const sheet = SpreadsheetApp.getActiveSheet();
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) { Browser.msgBox("沒有資料"); return; }

  const range = sheet.getRange(2, 2, lastRow - 1, 2); 
  const data = range.getValues();

  let updates = [];
  let hasUpdates = false;

  for (let i = 0; i < data.length; i++) {
    const name = data[i][0];
    let code = data[i][1];

    if (name && (!code || code === "")) {
      try {
        console.log(`正在查詢代號: ${name}`);
        // 這裡會自動呼叫新的 callGemini (包含 Token)
        const result = queryStockCode(name);
        const cleanCode = result.toString().split('.')[0]; 

        if (cleanCode.length >= 4) {
          updates.push([cleanCode]);
          hasUpdates = true;
        } else {
          updates.push([code]);
        }
      } catch (e) {
        console.error(e);
        updates.push([code]);
      }
    } else {
      updates.push([code]);
    }
  }

  if (hasUpdates) {
    sheet.getRange(2, 3, updates.length, 1).setValues(updates);
    SpreadsheetApp.flush();
    Browser.msgBox("代號更新完成！");
  } else {
    Browser.msgBox("無需更新。");
  }
}

/**
 * 功能 2: 核心分析邏輯
 */
function analyzeAllSheets() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheets = ss.getSheets();
  let processedCount = 0;

  // 1. 讀取 Prompt
  let customPrompt = "";
  try {
    customPrompt = DocumentApp.openById(PROMPT_FILE_ID).getBody().getText();
  } catch (e) {
    Browser.msgBox("讀取 Prompt 失敗: " + e.message);
    return;
  }

  // 2. 掃描所有 Sheet
  for (let i = 0; i < sheets.length; i++) {
    const sheet = sheets[i];
    const email = sheet.getRange("A2").getValue();

    if (email && email.toString().includes("@")) {
      processSheet(sheet, email, customPrompt);
      processedCount++;
    }
  }

  if (processedCount > 0) {
    Browser.msgBox(`已完成 ${processedCount} 個分頁的分析`);
  } else {
    Browser.msgBox("未發現有效的 Sheet (A2 必須有 Email)");
  }
}

function processSheet(sheet, email, promptContent) {
  const sheetName = sheet.getName();
  sheet.getRange("A5").setValue("分析進行中..."); 
  SpreadsheetApp.flush();

  const lastRow = sheet.getLastRow();
  if (lastRow < 2) return;

  const data = sheet.getRange(2, 2, lastRow - 1, 3).getValues();

  let reportContent = "";
  let successCount = 0;

  for (let i = 0; i < data.length; i++) {
    const stockName = data[i][0];       
    let stockCode = data[i][1];         
    const cost = data[i][2];            

    if (stockName) {
      try {
        // --- 自動查代號邏輯 ---
        if (!stockCode || stockCode.toString().trim() === "") {
          try {
            console.log(`發現 ${stockName} 缺代號，正在自動查詢...`);
            const result = queryStockCode(stockName);
            const cleanCode = result.toString().split('.')[0]; 

            if (cleanCode.length >= 4) {
              stockCode = cleanCode; 
              sheet.getRange(i + 2, 3).setValue(stockCode);
              console.log(`已自動填入代號: ${stockName} -> ${stockCode}`);
            }
          } catch (e) {
            console.log(`自動查代號失敗: ${e.message}`);
          }
        }

        // --- 開始分析 ---
        let userQuestion = "";

        if (cost && cost.toString() !== "") {
          userQuestion = `我持有「${stockName} (${stockCode})」，我的成本均價在 ${cost}。請根據現價與我的成本位階，給出明確的操作策略 (包含停損停利點)。`;
        } else {
          userQuestion = `請分析「${stockName} (${stockCode})」，並進行技術面與基本面分析，給出短線操作建議。`;
        }

        console.log("Ask Gemini: " + userQuestion);

        const analysis = callGemini(userQuestion, promptContent);
        const formattedAnalysis = formatMarkdown(analysis);

        reportContent += `
          <div style="margin-bottom: 30px; border: 1px solid #ddd; padding: 15px; border-radius: 8px; background-color: #f9f9f9;">
            <h3 style="margin-top: 0; color: #2c3e50; border-bottom: 1px solid #eee; padding-bottom: 8px;">
              ${stockName} (${stockCode || "代號查詢中"}) 
              ${cost ? `<span style="font-size:0.8em; color:#e74c3c; font-weight:normal;"> / (成本: ${cost})</span>` : ""}
            </h3>
            <div style="line-height: 1.6; color: #333; font-size: 14px;">${formattedAnalysis}</div>
          </div>
        `;
        successCount++;

      } catch (e) {
        reportContent += `<div style="color:red; padding:10px;">${stockName} 分析失敗: ${e.message}</div>`;
        console.error(e);
      }
    }
  }

  if (successCount > 0) {
    sendSummaryEmail(email, reportContent, sheetName);
    const now = new Date();
    sheet.getRange("A5").setValue(`已寄信 ${Utilities.formatDate(now, Session.getScriptTimeZone(), "yyyy/MM/dd HH:mm")}`);
  }
}

// ==========================================
// 3. 核心工具函式 (包含驗證邏輯)
// ==========================================

/**
 * 取得 Firebase ID Token (含快取機制)
 * 避免每次呼叫 API 都重新登入
 */
function getFirebaseToken() {
  const cache = CacheService.getScriptCache();
  const cachedToken = cache.get("firebase_token");
  
  if (cachedToken) {
    return cachedToken;
  }

  // 呼叫 Firebase Identity Toolkit 換取 Token
  const authUrl = `https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=${FIREBASE_API_KEY}`;
  const payload = {
    email: FIREBASE_EMAIL,
    password: FIREBASE_PASSWORD,
    returnSecureToken: true
  };

  const options = {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };

  const response = UrlFetchApp.fetch(authUrl, options);
  const result = JSON.parse(response.getContentText());

  if (response.getResponseCode() !== 200) {
    throw new Error("Firebase 登入失敗: " + (result.error ? result.error.message : "未知錯誤"));
  }

  const token = result.idToken;
  // Firebase Token 有效期 1 小時，我們快取 50 分鐘即可
  cache.put("firebase_token", token, 3000); 
  return token;
}

/**
 * 核心 API 呼叫工具 (包含重試機制)
 */
function callApi(path, payload, systemPrompt) {
  // 1. 先取得 Token
  let token;
  try {
    token = getFirebaseToken();
  } catch (e) {
    throw new Error("無法取得授權 Token: " + e.message);
  }

  // 如果有 systemPrompt，注入到 payload
  if (systemPrompt) {
    payload["system_prompt"] = systemPrompt;
  }
  
  const options = { 
    "method": "post", 
    "contentType": "application/json", 
    "headers": {
      "Authorization": "Bearer " + token 
    },
    "payload": JSON.stringify(payload), 
    "muteHttpExceptions": true 
  };

  const maxRetries = 3;
  let lastError = null;

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      const response = UrlFetchApp.fetch(GATEWAY_URL + path, options);
      const responseCode = response.getResponseCode();
      const content = response.getContentText();

      if (responseCode === 200) {
        return JSON.parse(content);
      } else if (responseCode === 504 || responseCode === 502) {
        // 遇到 Gateway Timeout 或 Bad Gateway 進行重試
        console.warn(`第 ${attempt} 次嘗試失敗 (${responseCode})，正在重試...`);
        lastError = `API Error ${responseCode}: ${content}`;
        if (attempt < maxRetries) {
          Utilities.sleep(Math.pow(2, attempt) * 1000); // 指數退避
          continue;
        }
      } else if (responseCode === 401) {
        throw new Error("401 Unauthorized: Token 無效或 Gateway 拒絕存取");
      } else {
        throw new Error(`API Error ${responseCode}: ${content}`);
      }
    } catch (e) {
      lastError = e.message;
      if (attempt < maxRetries) {
        console.warn(`第 ${attempt} 次連線失敗，正在重試: ${e.message}`);
        Utilities.sleep(2000);
        continue;
      }
    }
  }

  throw new Error(`${lastError} (已重試 ${maxRetries} 次後放棄)`);
}

/**
 * 舊版相容性包裝
 */
function callGemini(text, systemPrompt) {
  const result = callApi("/task", { "question": text }, systemPrompt);
  return result.answer;
}

/**
 * 查詢股票代號
 */
function queryStockCode(name) {
  const result = callApi("/ticker", { "name": name });
  return result.ticker;
}

function formatMarkdown(text) {
  if (!text) return "";
  let html = text;
  html = html.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>');
  html = html.replace(/^### (.*$)/gim, '<h4 style="margin: 10px 0 5px; color: #444;">$1</h4>');
  html = html.replace(/^\* (.*$)/gim, '• $1<br>');
  html = html.replace(/\n/g, '<br>');
  return html;
}

function sendSummaryEmail(recipient, contentBody, sheetName) {
  MailApp.sendEmail({
    to: recipient,
    subject: `【投資組合日報】${sheetName} - ${Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "MM/dd")} 分析報告`,
    htmlBody: `
      <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
        <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">📊 ${sheetName} 持股健檢</h2>
        ${contentBody}
        <br><p style="color:#999; font-size:12px;">Generated by Gemini AI (Secure Gateway)</p>
      </div>
    `
  });
}