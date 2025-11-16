# 需求文件

## 簡介

本功能旨在開發一個基於 Python 3.13 和 instaloader 套件的 Instagram 媒體下載工具。該系統允許使用者下載指定 Instagram 帳號的貼文中的圖片和影片，並將其儲存到本地檔案系統。

## 術語表

- **IG Downloader**：Instagram 媒體下載系統
- **Instaloader**：用於下載 Instagram 內容的 Python 套件
- **使用者**：執行下載操作的人員
- **目標帳號**：要下載媒體內容的 Instagram 帳號
- **媒體檔案**：Instagram 貼文中的圖片或影片
- **下載目錄**：儲存下載媒體檔案的本地資料夾

## 需求

### 需求 1

**使用者故事：** 作為使用者，我想要能夠指定一個 Instagram 帳號名稱，以便下載該帳號的所有公開貼文媒體。

#### 驗收標準

1. THE IG Downloader SHALL 接受一個 Instagram 帳號名稱作為輸入參數
2. WHEN 使用者提供有效的帳號名稱時，THE IG Downloader SHALL 連接到 Instagram 並擷取該帳號的貼文資訊
3. IF 提供的帳號名稱不存在，THEN THE IG Downloader SHALL 顯示錯誤訊息並終止執行
4. THE IG Downloader SHALL 下載目標帳號中所有可存取的圖片檔案
5. THE IG Downloader SHALL 下載目標帳號中所有可存取的影片檔案

### 需求 2

**使用者故事：** 作為使用者，我想要將下載的媒體檔案組織化地儲存在本地，以便日後能夠輕鬆找到和管理這些檔案。

#### 驗收標準

1. THE IG Downloader SHALL 建立一個以目標帳號名稱命名的下載目錄
2. WHEN 下載目錄不存在時，THE IG Downloader SHALL 自動建立該目錄
3. THE IG Downloader SHALL 將每個媒體檔案儲存到對應的下載目錄中
4. THE IG Downloader SHALL 保留媒體檔案的原始檔名或使用有意義的命名規則
5. IF 下載目錄已存在相同檔名的檔案，THEN THE IG Downloader SHALL 跳過該檔案的下載

### 需求 3

**使用者故事：** 作為使用者，我想要在下載過程中看到進度資訊，以便了解下載狀態和預估完成時間。

#### 驗收標準

1. WHEN 開始下載時，THE IG Downloader SHALL 顯示目標帳號的基本資訊
2. WHILE 下載進行中，THE IG Downloader SHALL 顯示當前正在處理的貼文資訊
3. THE IG Downloader SHALL 在每個媒體檔案下載完成後顯示確認訊息
4. WHEN 所有下載完成時，THE IG Downloader SHALL 顯示下載摘要統計資訊
5. THE IG Downloader SHALL 顯示下載的總檔案數量和儲存位置

### 需求 4

**使用者故事：** 作為使用者，我想要能夠處理下載過程中的錯誤情況，以便系統能夠穩定運行並提供有用的錯誤資訊。

#### 驗收標準

1. IF 網路連線失敗，THEN THE IG Downloader SHALL 顯示網路錯誤訊息並提供重試選項
2. IF Instagram API 回應錯誤，THEN THE IG Downloader SHALL 記錄錯誤詳情並繼續處理其他貼文
3. IF 磁碟空間不足，THEN THE IG Downloader SHALL 顯示警告訊息並停止下載
4. IF 檔案寫入權限不足，THEN THE IG Downloader SHALL 顯示權限錯誤訊息並終止執行
5. THE IG Downloader SHALL 記錄所有錯誤到日誌檔案中以供除錯使用

### 需求 5

**使用者故事：** 作為使用者，我想要使用 uv 作為套件管理工具，以便快速且可靠地管理專案依賴。

#### 驗收標準

1. THE IG Downloader SHALL 使用 uv 作為 Python 套件管理工具
2. THE IG Downloader SHALL 提供 pyproject.toml 檔案定義專案依賴
3. THE IG Downloader SHALL 相容於 Python 3.13 版本
4. THE IG Downloader SHALL 將 instaloader 列為核心依賴套件
5. WHEN 使用者執行安裝指令時，THE IG Downloader SHALL 透過 uv 安裝所有必要的依賴套件

### 需求 6

**使用者故事：** 作為使用者，我想要能夠下載目標帳號的 Stories，以便保存這些限時動態內容。

#### 驗收標準

1. WHERE 使用者啟用 Stories 下載選項，THE IG Downloader SHALL 下載目標帳號的所有可用 Stories
2. THE IG Downloader SHALL 將 Stories 儲存在獨立的子目錄中
3. WHEN Stories 不存在或已過期時，THE IG Downloader SHALL 顯示提示訊息並繼續執行
4. THE IG Downloader SHALL 在下載摘要中顯示 Stories 的下載數量
5. THE IG Downloader SHALL 優先下載 Stories 再下載一般貼文

### 需求 7

**使用者故事：** 作為使用者，我想要能夠使用多執行緒並行下載，以便加快大量媒體檔案的下載速度。

#### 驗收標準

1. WHERE 使用者指定執行緒數量，THE IG Downloader SHALL 使用指定數量的執行緒進行並行下載
2. THE IG Downloader SHALL 預設使用單執行緒模式以避免對伺服器造成過大負擔
3. THE IG Downloader SHALL 限制最大執行緒數量不超過 8 個
4. WHILE 多執行緒下載進行中，THE IG Downloader SHALL 確保統計資料更新的執行緒安全性
5. IF 任一執行緒發生錯誤，THEN THE IG Downloader SHALL 記錄錯誤並繼續其他執行緒的下載作業

### 需求 8

**使用者故事：** 作為使用者，我想要能夠下載目標帳號的 Reels 短影片，以便收藏這些創意內容。

#### 驗收標準

1. WHERE 使用者啟用 Reels 下載選項，THE IG Downloader SHALL 下載目標帳號的所有 Reels 影片
2. THE IG Downloader SHALL 將 Reels 儲存在獨立的子目錄中
3. THE IG Downloader SHALL 正確識別貼文是否為 Reel 類型
4. THE IG Downloader SHALL 在下載摘要中顯示 Reels 的下載數量
5. WHEN Reels 不存在時，THE IG Downloader SHALL 顯示提示訊息並繼續執行

### 需求 9

**使用者故事：** 作為使用者，我想要在下載中斷後能夠從上次中斷處繼續下載，以便節省時間和頻寬。

#### 驗收標準

1. THE IG Downloader SHALL 預設啟用斷點續傳功能
2. THE IG Downloader SHALL 在下載目錄中建立進度記錄檔案
3. WHEN 開始下載時，THE IG Downloader SHALL 載入先前的下載進度
4. THE IG Downloader SHALL 跳過已下載的貼文和媒體檔案
5. THE IG Downloader SHALL 在每個貼文下載完成後立即更新進度記錄
6. IF 進度記錄檔案損壞或無法讀取，THEN THE IG Downloader SHALL 從頭開始下載
7. THE IG Downloader SHALL 在下載摘要中顯示是否為續傳模式

### 需求 10

**使用者故事：** 作為使用者，我想要能夠透過貼文 URL 下載單一貼文，以便快速獲取特定貼文的媒體內容而不需要下載整個帳號。

#### 驗收標準

1. THE IG Downloader SHALL 接受 Instagram 貼文 URL 作為輸入參數
2. WHEN 使用者提供貼文 URL 時，THE IG Downloader SHALL 從 URL 中提取貼文的 shortcode
3. THE IG Downloader SHALL 使用 shortcode 擷取該貼文的資訊
4. THE IG Downloader SHALL 下載該貼文中的所有媒體檔案（圖片或影片）
5. IF 貼文 URL 格式不正確，THEN THE IG Downloader SHALL 顯示錯誤訊息並終止執行
6. IF 貼文不存在或無法存取，THEN THE IG Downloader SHALL 顯示錯誤訊息並終止執行
7. THE IG Downloader SHALL 將單一貼文的媒體儲存到指定的輸出目錄中
8. WHEN 下載單一貼文時，THE IG Downloader SHALL 顯示貼文的基本資訊（作者、日期等）
