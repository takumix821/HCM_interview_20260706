# 保健闢謠文章蒐集

蒐集衛生福利部國民健康署網站「保健闢謠」分類的文章內容。

首頁 > 服務園地 > 真相與闢謠 > 保健闢謠
（文章列表來源：`https://www.hpa.gov.tw/Pages/TopicList.aspx?idx=0&nodeid=127`，翻頁靠 `idx` 參數）

## 需求對照

| 題目要求 | 實作方式 |
|---|---|
| 初始化蒐集前 10 篇，儲存 csv | 第一次執行時 `articles/` 資料夾是空的，程式會把文章列表最新的前 10 篇全部視為新文章並存檔（不足 10 篇會自動翻到下一頁 `idx=1, 2, ...` 湊滿） |
| 增量蒐集，資料源有比 csv 新的文章時，更新增加篇數 | 之後每次執行，會由新到舊比對文章列表的 pid，遇到已經存過的 pid 就停止（後面一定更舊），只把真正新的文章抓下來存檔；不受篇數上限，一次新增再多篇也不會漏抓 |

## 環境需求

- Python 3.9+
- [uv](https://docs.astral.sh/uv/)（本專案用 uv 管理套件與虛擬環境）

## 安裝

在專案根目錄執行：

```bash
uv sync
```

會自動建立虛擬環境並安裝 `pyproject.toml` 裡列的套件（requests、beautifulsoup4、certifi）。

## 執行方式

```bash
uv run collect_articles.py
```

- **第一次執行**：`articles/articles.csv` 還不存在 → 抓文章列表最新前 10 篇的標題與內文，寫入 `articles.csv`（初始化蒐集）。
- **之後重複執行**：抓 `articles.csv` 裡還沒出現過的 pid，由新到舊一路檢查到遇到已存過的 pid 為止，各自新增一列（增量蒐集）；如果網站沒有新文章，會印出「沒有新文章，資料已是最新。」且不會重複下載。

執行過程中，每抓一篇文章會先印一行「處理中：[pid] 標題」的進度訊息，同時寫入 csv；全部抓完後，會把新增文章的 pid、標題再印一次做總結。

若要調整初始化時抓取的篇數，改 `collect_articles.py` 檔案最上方的常數：

```python
TOP_N = 10  # 預設抓前 10 篇
```

## 容器化執行（含排程自動更新）

```bash
docker compose up --build -d   # 啟動：容器啟動先跑一次蒐集，之後照排程（預設每 10 分鐘）自動更新
docker compose logs -f         # 看即時執行紀錄
docker compose down            # 停止（articles/ 是 volume，資料還留在 host）
```

蒐集結果一樣輸出到 `./articles/`，跟本機直接執行的存放位置一致。排程頻率可以改 `scheduler/crontab` 裡的時間設定，改完重新 `docker compose up --build -d` 生效。

## 結果存放位置

所有蒐集到的文章存放在同一個檔案 `articles/articles.csv`，**每篇文章是一列資料**：

| 欄位 | 說明 |
|---|---|
| pid | 文章在網站上的識別碼，用來判斷文章是否已蒐集過 |
| title | 文章標題 |
| content | 文章內文（純文字，已去除 HTML 標籤） |

第一次執行會建立這個檔案並寫入標頭列，之後每次增量蒐集到新文章，都會在檔案後面新增一列，不會重寫整個檔案。csv 以 `utf-8-sig` 編碼存檔，用 Excel 開啟中文不會亂碼。

## 補充說明：SSL 憑證

`www.hpa.gov.tw` 的伺服器只回傳它自己的憑證，沒有附上簽發它的 TWCA 中繼憑證（intermediate CA），一般信任庫（含 Python 的 certifi）都沒有內建這張中繼憑證，直接連線會出現 `CERTIFICATE_VERIFY_FAILED` 錯誤。

已在 `certs/twca_secure_ssl_intermediate.pem` 內附上這張中繼憑證，`collect_articles.py` 執行時會自動把它跟 certifi 的憑證庫合併使用，不需要額外設定或關閉憑證驗證。

另外，`hpa.gov.tw` 的回應速度不太穩定（單一請求偶爾要 15-20 秒），已對外部請求加上 30 秒 timeout，避免程式無限期卡住。

## 專案結構

```
.
├── collect_articles.py   # 主程式：初始化蒐集 + 增量蒐集
├── certs/                # TWCA 中繼憑證（SSL 修正用）
├── articles/              # 蒐集結果（執行後自動產生，articles.csv 每篇文章一列）
├── scheduler/             # 容器化排程用的 shell script
├── Dockerfile             # 容器化用
├── docker-compose.yml     # 容器化用
├── pyproject.toml         # 套件依賴
└── uv.lock
```
