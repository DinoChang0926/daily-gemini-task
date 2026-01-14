// ==========================================
// 1. 全域設定區 (請務必填寫)
// ==========================================
const API_URL = "";
const API_KEY = "";
const PROMPT_FILE_ID = ""; // google doc

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
 * 功能 1: 自動填寫 C 欄代號 (保留此功能，因為代號對 AI 搜尋很有幫助)
 */
function autoFillTickers() {
  const sheet = SpreadsheetApp.getActiveSheet();
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) { Browser.msgBox("沒有資料"); return; }

  const range = sheet.getRange(2, 2, lastRow - 1, 2); // 讀取 B(名稱), C(代號)
  const data = range.getValues();

  let updates = [];
  let hasUpdates = false;

  for (let i = 0; i < data.length; i++) {
    const name = data[i][0];
    let code = data[i][1];

    if (name && (!code || code === "")) {
      try {
        console.log(`正在查詢代號: ${name}`);
        const result = callGemini(`請提供台灣股市「${name}」的股票代號。只輸出4位數字，不要有文字。`, "Output ONLY the 4-digit ticker.");
        const cleanCode = result.toString().replace(/[^\d]/g, '');

        if (cleanCode.length >= 4) {
          updates.push([cleanCode]);
          hasUpdates = true;
        } else {
          updates.push([code]);
        }
      } catch (e) {
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
 * 功能 2: 核心分析邏輯 (已移除本地查價)
 */
// ==========================================
// 2. 主程式邏輯 (自動補全代號 + 分析)
// ==========================================

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

    // 簡單檢查 A2 是否有 Email，有的話才處理
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
  sheet.getRange("A5").setValue("分析進行中..."); // 更新狀態
  SpreadsheetApp.flush();

  const lastRow = sheet.getLastRow();
  if (lastRow < 2) return;

  // 讀取範圍：B欄(名稱), C欄(代號), D欄(成本)
  // getRange(row, col, numRows, numCols) -> 從第2列第2欄(B)開始，讀取3欄寬(B,C,D)
  const data = sheet.getRange(2, 2, lastRow - 1, 3).getValues();

  let reportContent = "";
  let successCount = 0;

  for (let i = 0; i < data.length; i++) {
    const stockName = data[i][0];       // B欄
    let stockCode = data[i][1];         // C欄 (可能會是空的)
    const cost = data[i][2];            // D欄

    if (stockName) {
      try {
        // --- 🔥 新增功能：如果代號是空的，自動幫忙查並填回去 ---
        if (!stockCode || stockCode.toString().trim() === "") {
          try {
            // 呼叫 AI 查代號
            console.log(`發現 ${stockName} 缺代號，正在自動查詢...`);
            const tickerPrompt = `請提供台灣股市「${stockName}」的股票代號。只輸出4位數字，不要有其他文字。`;
            const result = callGemini(tickerPrompt, "Output ONLY the 4-digit ticker.");
            const cleanCode = result.toString().replace(/[^\d]/g, '');

            if (cleanCode.length >= 4) {
              stockCode = cleanCode; // 更新變數，讓等下的分析報告可以用
              // 【關鍵】寫回 Google Sheet (列號=i+2, 欄號=3即C欄)
              sheet.getRange(i + 2, 3).setValue(stockCode);
              console.log(`已自動填入代號: ${stockName} -> ${stockCode}`);
            }
          } catch (e) {
            console.log(`自動查代號失敗: ${e.message}`);
            // 失敗就算了，繼續往下跑分析
          }
        }

        // --- 開始分析 (這時候 stockCode 應該已經有值了) ---
        let userQuestion = "";

        // 組合指令
        if (cost && cost.toString() !== "") {
          userQuestion = `我持有「${stockName} (${stockCode})」，我的成本均價在 ${cost}。請務必自行搜尋最新股價，並根據搜尋到的現價與我的成本位階，給出明確的操作策略 (包含停損停利點)。`;
        } else {
          userQuestion = `請分析「${stockName} (${stockCode})」，請務必自行搜尋最新股價，並進行技術面與基本面分析，給出短線操作建議。`;
        }

        console.log("Ask Gemini: " + userQuestion);

        const analysis = callGemini(userQuestion, promptContent);
        const formattedAnalysis = formatMarkdown(analysis);

        // --- 生成 HTML 卡片 ---
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
// 3. 工具函式
// ==========================================

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
        <br><p style="color:#999; font-size:12px;">Generated by Gemini AI (with Google Search)</p>
      </div>
    `
  });
}

function callGemini(text, systemPrompt) {
  const payload = { "question": text, "system_prompt": systemPrompt, "secret": API_KEY };
  const options = { "method": "post", "contentType": "application/json", "payload": JSON.stringify(payload), "muteHttpExceptions": true };
  const response = UrlFetchApp.fetch(API_URL, options);
  if (response.getResponseCode() === 200) {
    return JSON.parse(response.getContentText()).answer;
  } else {
    throw new Error(`API Error ${response.getResponseCode()}`);
  }
}