"""

https://www.hpa.gov.tw/Pages/TopicList.aspx?idx=0&nodeid=127

執行方式：
    uv run collect_articles.py

行為：蒐集衛生福利部國民健康署「保健闢謠」文章
路徑：首頁 > 服務園地 > 真相與闢謠 > 保健闢謠

    - 第一次執行：資料夾 articles/ 是空的，會把文章列表最新的前 TOP_N 篇
      全部視為「新文章」，逐篇存成一個 csv（初始化蒐集）。
    - 之後再執行：只會把 articles/ 裡還沒出現過的 pid 抓下來、存檔
      （增量蒐集），已經蒐集過的文章不會重複下載內文。
"""

import csv
import tempfile
from itertools import islice
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import certifi
import requests
from bs4 import BeautifulSoup

LIST_URL = "https://www.hpa.gov.tw/Pages/TopicList.aspx?idx={idx}&nodeid=127"
BASE_URL = "https://www.hpa.gov.tw"
DATA_DIR = Path(__file__).parent / "articles"
TOP_N = 10  # 預設抓前 N 篇，呼叫 update(n=...) 可覆寫

# TWCA 中繼憑證
INTERMEDIATE_CERT = Path(__file__).parent / "certs" / "twca_secure_ssl_intermediate.pem"


def ca_bundle_with_twca_intermediate() -> str:
    bundle = Path(certifi.where()).read_text() + INTERMEDIATE_CERT.read_text()
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False)
    tmp.write(bundle)
    tmp.close()
    return tmp.name


CA_BUNDLE = ca_bundle_with_twca_intermediate()
HEADERS = {"User-Agent": "Mozilla/5.0"}


def fetch_soup(url: str) -> BeautifulSoup:
    resp = requests.get(url, headers=HEADERS, verify=CA_BUNDLE, timeout=30)
    resp.encoding = resp.apparent_encoding
    return BeautifulSoup(resp.text, "html.parser")


def extract_pid(link: str) -> str:
    return parse_qs(urlparse(link).query)["pid"][0]


def fetch_article_content(link: str) -> str:
    """文章列表沒有內文，內文要另外到文章詳細頁抓（同 script.py）。"""
    soup = fetch_soup(link)
    content = soup.select_one("div.contentBlock")
    return content.get_text("\n", strip=True) if content else ""


def iter_list_entries():
    """
    由新到舊走訪文章列表頁（idx=0, 1, 2, ...），逐篇 yield pid / 標題 / 連結。
    一頁抓不滿就自動翻下一頁，直到某頁抓不到任何文章為止。
    """
    idx = 0
    while True:
        soup = fetch_soup(LIST_URL.format(idx=idx))
        anchors = soup.select("ul.infoList div.listBox a")
        if not anchors:
            return
        for a in anchors:
            link = urljoin(BASE_URL, a.get("href"))
            yield {"pid": extract_pid(link), "title": a.get_text(strip=True), "link": link}
        idx += 1


def get_existing_pids() -> set[str]:
    """已收錄文章的 pid，用 articles/ 資料夾裡既有 csv 檔名的前綴推回。"""
    if not DATA_DIR.exists():
        return set()
    return {path.name.split("_", 1)[0] for path in DATA_DIR.glob("*.csv")}


def save_article(article: dict) -> Path:
    DATA_DIR.mkdir(exist_ok=True)
    filename = f"{article['pid']}_{article['title']}.csv"
    path = DATA_DIR / filename
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["pid", "title", "content"])
        writer.writerow([article["pid"], article["title"], article["content"]])
    return path


def update(n: int = TOP_N) -> list[dict]:
    """
    由新到舊檢查文章列表，遇到 pid 已經收錄過就停止（後面的一定更舊）。
    尚未收錄的文章才會去抓內文並存檔，避免重複下載已存在的內容。

    第一次執行（articles/ 是空的）只抓最新 n 篇；之後執行不受 n 限制，
    一路往舊翻到遇到已收錄過的 pid 為止，避免一次新增超過 n 篇時漏抓。
    """
    existing_pids = get_existing_pids()
    entries = iter_list_entries() if existing_pids else islice(iter_list_entries(), n)

    new_articles = []
    for entry in entries:
        if entry["pid"] in existing_pids:
            break
        print(f"處理中：[{entry['pid']}] {entry['title']}", flush=True)
        article = {
            "pid": entry["pid"],
            "title": entry["title"],
            "content": fetch_article_content(entry["link"]),
        }
        save_article(article)
        new_articles.append(article)

    return new_articles


if __name__ == "__main__":
    new_articles = update(TOP_N)

    if not new_articles:
        print("沒有新文章，資料已是最新。")
    else:
        print(f"新增 {len(new_articles)} 篇文章：\n")
        for article in new_articles:
            print(f"[{article['pid']}] {article['title']}")
            print(article["content"])
            print("---")
