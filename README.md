# Instagram 媒體下載工具

一個基於 Python 3.13 和 [instaloader](https://instaloader.github.io/) 的 Instagram 媒體下載命令列工具，可以下載指定使用者的公開貼文、Stories 和 Reels。

## ✨ 功能特色

- 📥 下載 Instagram 使用者的所有公開貼文（圖片和影片）
- 📖 支援下載 Stories（限時動態）
- 🎬 支援下載 Reels（短影片）
- 🔄 斷點續傳功能，中斷後可從上次位置繼續下載
- ⚡ 多執行緒並行下載，加快下載速度
- 📊 詳細的下載統計和進度顯示
- 🗂️ 自動組織檔案結構，分類儲存不同類型的媒體
- 🛡️ 完善的錯誤處理和日誌記錄

## 📋 系統需求

- Python 3.13 或更高版本
- [uv](https://docs.astral.sh/uv/) 套件管理工具

## 🚀 安裝

### 1. 安裝 uv

如果尚未安裝 uv，請先安裝：

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows:**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

或使用 pip：
```bash
pip install uv
```

### 2. 安裝 IG Media Downloader

克隆或下載此專案後，在專案目錄中執行：

```bash
# 安裝專案及其依賴
uv pip install -e .
```

安裝完成後，`ig-download` 命令將可在系統中使用。

## 📖 使用方法

### 模式 1: 下載使用者的所有貼文

下載指定使用者的所有公開貼文：

```bash
ig-download <username>
```

例如：
```bash
ig-download instagram
```

### 模式 2: 下載單一貼文（透過 URL）

下載特定的單一貼文：

```bash
ig-download --url <Instagram貼文URL>
```

例如：
```bash
ig-download --url https://www.instagram.com/p/ABC123xyz/
ig-download --url https://www.instagram.com/reel/XYZ789abc/
```

### 模式 3: 批次下載多個貼文（從 YAML 檔案）

從 YAML 檔案批次下載多個貼文：

```bash
ig-download --url-file urls.yaml
```

YAML 檔案格式範例：

```yaml
# urls.yaml
urls:
  - url: https://www.instagram.com/p/ABC123xyz/
    description: "範例貼文 1"
  
  - url: https://www.instagram.com/p/DEF456uvw/
    description: "範例貼文 2"
  
  - url: https://www.instagram.com/reel/GHI789rst/
    description: "範例 Reel"

# 也支援簡化格式（僅 URL 列表）
# urls:
#   - https://www.instagram.com/p/ABC123xyz/
#   - https://www.instagram.com/p/DEF456uvw/
```

### 進階選項

#### 指定輸出目錄

```bash
ig-download username --output-dir ~/Downloads/instagram
ig-download --url https://www.instagram.com/p/ABC123xyz/ --output-dir ~/Downloads
```

#### 下載 Stories 和 Reels（僅適用於使用者模式）

```bash
# 下載 Stories
ig-download username --include-stories

# 下載 Reels
ig-download username --include-reels

# 同時下載 Stories 和 Reels
ig-download username --include-stories --include-reels
```

#### 限制下載數量

```bash
# 只下載最新的 50 個貼文
ig-download username --max-posts 50
```

#### 多執行緒並行下載

```bash
# 使用 4 個執行緒並行下載（建議不超過 4）
ig-download username --workers 4

# 批次下載時使用多執行緒
ig-download --url-file urls.yaml --workers 4
```

#### 停用斷點續傳

```bash
# 從頭開始下載，不使用之前的進度
ig-download username --no-resume
```

### 批次下載特色功能

#### 自動重試機制

批次下載時，如果某個 URL 下載失敗，系統會自動重試最多 3 次，每次重試之間會有遞增的等待時間（2秒、4秒、6秒）。

#### 失敗記錄

下載失敗的 URL 會自動記錄到 `failed_downloads.yaml` 檔案中，包含失敗原因和時間戳記：

```yaml
failed_downloads:
  - url: https://www.instagram.com/p/ABC123xyz/
    error: "ConnectionException: Network timeout"
    timestamp: "2024-01-16T15:30:00"
```

#### 進度條顯示

批次下載時會顯示即時進度條，包含：
- 當前進度（已完成/總數）
- 成功和失敗的數量
- 預估剩餘時間
```

### 完整範例

```bash
# 下載使用者的所有內容，使用 4 個執行緒，限制 100 個貼文
ig-download username \
  --include-stories \
  --include-reels \
  --workers 4 \
  --max-posts 100 \
  --output-dir ~/Downloads/instagram
```

## 📁 檔案結構

下載的檔案會按照以下結構組織：

```
output_dir/
└── username/
    ├── posts/                    # 一般貼文
    │   ├── 2024-01-15_ABC123_1.jpg
    │   ├── 2024-01-15_ABC123_2.jpg
    │   └── 2024-01-14_XYZ789_1.mp4
    ├── stories/                  # Stories（如果啟用）
    │   ├── 2024-01-16_story_1.jpg
    │   └── 2024-01-16_story_2.mp4
    ├── reels/                    # Reels（如果啟用）
    │   ├── 2024-01-15_reel_ABC123.mp4
    │   └── 2024-01-14_reel_XYZ789.mp4
    └── .download_progress.json   # 下載進度記錄
```

## 🔧 命令列參數

| 參數 | 說明 | 預設值 |
|------|------|--------|
| `username` | Instagram 使用者名稱（必填） | - |
| `--output-dir` | 下載檔案的輸出目錄 | 當前目錄 |
| `--max-posts` | 限制下載的貼文數量 | 無限制 |
| `--include-stories` | 下載 Stories | 否 |
| `--include-reels` | 下載 Reels | 否 |
| `--workers` | 並行下載的執行緒數量 | 1 |
| `--no-resume` | 停用斷點續傳功能 | 啟用 |

## 💡 使用技巧

### 斷點續傳

工具預設啟用斷點續傳功能。如果下載過程中斷（網路問題、手動中斷等），再次執行相同命令即可從上次中斷處繼續：

```bash
# 第一次執行（中斷）
ig-download username

# 再次執行，會自動從上次中斷處繼續
ig-download username
```

進度資訊儲存在 `.download_progress.json` 檔案中。如果想從頭開始下載，可以：
- 使用 `--no-resume` 參數
- 或刪除 `.download_progress.json` 檔案

### 多執行緒下載

使用多執行緒可以加快下載速度，但建議不要設定過高的執行緒數量，以避免對 Instagram 伺服器造成過大負擔：

```bash
# 推薦：使用 2-4 個執行緒
ig-download username --workers 4
```

### Stories 時效性

Stories 在發布後 24 小時內有效，建議優先下載 Stories：

```bash
ig-download username --include-stories
```

## 🐛 常見問題與故障排除

### Q: 出現「帳號不存在」錯誤

**A:** 請檢查以下項目：
- 確認使用者名稱拼寫正確
- 確認該帳號確實存在且未被刪除
- 嘗試在瀏覽器中訪問 `https://www.instagram.com/<username>/` 確認帳號狀態

### Q: 出現「私人帳號」錯誤

**A:** 此工具目前僅支援下載公開帳號的內容。私人帳號需要登入且獲得追蹤許可才能存取，目前版本不支援此功能。

### Q: 網路連線失敗

**A:** 請嘗試以下解決方法：
- 檢查網路連線是否正常
- 確認防火牆或代理設定沒有阻擋連線
- 稍後再試（可能是 Instagram 伺服器暫時無法存取）
- 工具會自動重試 3 次，如果仍然失敗，請檢查網路設定

### Q: 磁碟空間不足

**A:** 
- 清理磁碟空間後再試
- 使用 `--max-posts` 參數限制下載數量
- 指定其他有足夠空間的目錄：`--output-dir /path/to/large/disk`

### Q: 檔案權限錯誤

**A:**
- 確認對輸出目錄有寫入權限
- 嘗試使用其他目錄或在當前使用者的家目錄下建立目錄
- Linux/macOS: 檢查目錄權限 `ls -la`

### Q: 下載速度很慢

**A:**
- 使用多執行緒下載：`--workers 4`
- 檢查網路連線速度
- Instagram 可能有速率限制，請耐心等待

### Q: 某些貼文下載失敗

**A:**
- 檢查日誌檔案 `ig_downloader.log` 查看詳細錯誤資訊
- 某些貼文可能因為權限或其他原因無法下載，工具會跳過並繼續下載其他貼文
- 錯誤數量會在下載摘要中顯示

### Q: Stories 顯示「不存在或已過期」

**A:**
- Stories 只保留 24 小時，過期後無法下載
- 確認該使用者確實有發布 Stories
- 嘗試在 Instagram 應用程式中確認 Stories 是否存在

### Q: 如何查看詳細的錯誤資訊？

**A:** 所有錯誤和詳細日誌都會記錄在 `ig_downloader.log` 檔案中：

```bash
# 查看日誌檔案
cat ig_downloader.log

# 即時監控日誌
tail -f ig_downloader.log
```

### Q: 下載的檔案命名規則是什麼？

**A:** 檔案名稱格式為：`{發布日期}_{貼文代碼}_{媒體索引}.{副檔名}`

例如：`2024-01-15_ABC123_1.jpg`
- `2024-01-15`: 貼文發布日期
- `ABC123`: Instagram 貼文的唯一代碼
- `1`: 該貼文中的第幾個媒體檔案
- `jpg`: 檔案類型

### Q: 可以同時下載多個使用者嗎？

**A:** 目前版本一次只能下載一個使用者。如需下載多個使用者，請多次執行命令：

```bash
ig-download user1
ig-download user2
ig-download user3
```

或使用 shell 腳本：
```bash
#!/bin/bash
for user in user1 user2 user3; do
    ig-download "$user" --output-dir ~/Downloads/instagram
done
```

## 📝 日誌檔案

工具會自動記錄所有操作到 `ig_downloader.log` 檔案中，包括：
- 下載進度
- 錯誤訊息
- 警告資訊
- 除錯資訊

日誌檔案位於執行命令的當前目錄。

## ⚠️ 注意事項

1. **僅支援公開帳號**：此工具目前僅能下載公開帳號的內容
2. **遵守使用條款**：請遵守 Instagram 的使用條款和服務條款
3. **尊重版權**：下載的內容可能受版權保護，請勿用於商業用途
4. **速率限制**：避免使用過高的執行緒數量，以免被 Instagram 限制存取
5. **Stories 時效**：Stories 只保留 24 小時，請及時下載

## 🔄 更新

更新到最新版本：

```bash
# 拉取最新程式碼
git pull

# 重新安裝
uv pip install -e .
```

## 🙏 致謝

本專案基於 [instaloader](https://instaloader.github.io/) 套件開發，感謝 instaloader 團隊的優秀工作。

---

**免責聲明**：此工具僅供個人學習和研究使用。使用者應自行承擔使用本工具的所有責任，並遵守相關法律法規和 Instagram 的使用條款。
