# 實作計畫

- [x] 1. 建立專案結構和依賴配置
  - 建立 `pyproject.toml` 檔案，配置 Python 3.13 和 uv 套件管理
  - 定義專案依賴：instaloader 作為核心依賴
  - 建立基本的目錄結構：`ig_media_downloader/` 主套件目錄
  - _需求：5.1, 5.2, 5.3, 5.4_

- [x] 2. 實作資料模型
  - 建立 `models.py` 檔案
  - 實作 `DownloadStats` dataclass，包含所有統計欄位（貼文、Stories、Reels、續傳狀態）
  - 實作 `duration` 和 `total_files` 屬性方法
  - _需求：2.4, 2.5, 6.4, 8.4, 9.7_

- [x] 3. 實作日誌系統
  - 建立 `logger.py` 檔案
  - 實作 `setup_logger` 函數，配置檔案和控制台輸出
  - 設定適當的日誌格式和等級
  - _需求：4.5_

- [x] 4. 實作核心下載器類別基礎功能
  - 建立 `downloader.py` 檔案
  - 實作 `IGDownloader` 類別的 `__init__` 方法，初始化 instaloader 和執行緒鎖
  - 實作 `_create_output_directory` 方法，建立使用者專屬目錄結構
  - 實作基本的錯誤處理方法 `_handle_download_error`
  - _需求：2.1, 2.2, 4.2_

- [x] 5. 實作斷點續傳功能
  - 在 `downloader.py` 中實作 `_load_progress` 方法，從 JSON 檔案載入進度
  - 實作 `_save_progress` 方法，儲存下載進度到 JSON 檔案
  - 實作 `_is_already_downloaded` 方法，檢查貼文是否已下載
  - 加入進度檔案的錯誤處理（檔案損壞時的容錯機制）
  - _需求：9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

- [x] 6. 實作一般貼文下載功能
  - 實作 `_download_post` 方法，下載單一貼文的圖片和影片
  - 整合斷點續傳檢查，跳過已下載的貼文
  - 實作檔案存在檢查，避免重複下載
  - 加入下載進度的即時更新
  - _需求：1.1, 1.2, 1.4, 1.5, 2.3, 2.4, 9.4_

- [x] 7. 實作 Stories 下載功能
  - 實作 `download_stories` 方法
  - 使用 instaloader 的 `get_stories` API 獲取 Stories
  - 將 Stories 儲存到獨立的 `stories/` 子目錄
  - 處理 Stories 不存在或過期的情況
  - _需求：6.1, 6.2, 6.3_

- [x] 8. 實作 Reels 下載功能
  - 實作 `download_reels` 方法
  - 實作 `_is_reel` 輔助方法，識別 Reel 類型貼文
  - 將 Reels 儲存到獨立的 `reels/` 子目錄
  - 處理 Reels 不存在的情況
  - _需求：8.1, 8.2, 8.3, 8.5_

- [x] 9. 實作多執行緒並行下載
  - 實作 `_download_posts_parallel` 方法，使用 `ThreadPoolExecutor`
  - 加入執行緒鎖保護統計資料更新
  - 實作執行緒數量限制（最大 8 個）
  - 處理執行緒中的錯誤，確保不影響其他執行緒
  - _需求：7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 10. 實作主下載流程
  - 實作 `download_user_media` 方法，整合所有下載功能
  - 實作下載順序：Stories → Reels → 一般貼文
  - 根據參數決定是否下載 Stories 和 Reels
  - 根據參數決定使用單執行緒或多執行緒
  - 收集並返回 `DownloadStats` 統計資訊
  - _需求：1.2, 3.1, 3.2, 6.5_

- [x] 11. 實作錯誤處理機制
  - 處理帳號不存在的錯誤（`ProfileNotExistsException`）
  - 處理網路連線錯誤，實作重試機制（最多 3 次）
  - 處理私人帳號錯誤（`PrivateProfileException`）
  - 處理磁碟空間不足錯誤（`ENOSPC`）
  - 處理檔案權限錯誤（`EACCES`）
  - _需求：1.3, 4.1, 4.2, 4.3, 4.4_

- [x] 12. 實作命令列介面
  - 建立 `main.py` 檔案
  - 實作 `parse_arguments` 函數，使用 `argparse` 解析所有命令列參數
  - 實作 `display_summary` 函數，顯示下載摘要統計
  - 實作 `main` 函數，整合參數解析、下載器初始化和執行流程
  - 加入進度顯示（當前處理的貼文資訊）
  - _需求：1.1, 3.1, 3.3, 3.4, 3.5_

- [x] 13. 建立專案入口點和安裝配置
  - 在 `pyproject.toml` 中配置 `[project.scripts]` 入口點
  - 建立 `__init__.py` 檔案
  - 建立 `__main__.py` 檔案，支援 `python -m` 執行方式
  - _需求：5.5_

- [x] 14. 建立使用文件
  - 建立 `README.md` 檔案
  - 撰寫安裝說明（使用 uv 安裝）
  - 撰寫使用範例和參數說明
  - 撰寫常見問題和故障排除指南
  - _需求：1.1, 5.5_

- [x] 15. 撰寫測試
- [x] 15.1 建立測試結構
  - 建立 `tests/` 目錄
  - 配置 pytest 和相關測試依賴
  - _需求：所有需求_

- [x] 15.2 撰寫單元測試
  - 測試 `DownloadStats` 資料模型
  - 測試 `_load_progress` 和 `_save_progress` 方法
  - 測試 `_is_already_downloaded` 方法
  - 測試錯誤處理邏輯
  - _需求：2.4, 9.3, 9.4, 9.5, 4.1-4.4_

- [x] 15.3 撰寫整合測試
  - 使用 mock 測試完整下載流程
  - 測試多執行緒下載功能
  - 測試斷點續傳功能
  - 測試 Stories 和 Reels 下載
  - _需求：1.2, 6.1, 8.1, 7.1, 9.1_

- [x] 16. 更新專案依賴
  - 在 `pyproject.toml` 中新增 `pyyaml>=6.0` 依賴
  - 在 `pyproject.toml` 中新增 `tqdm>=4.66` 依賴
  - 執行 `uv pip install -e .` 更新依賴
  - _需求：10.1_

- [x] 17. 實作 URL 解析功能
- [x] 17.1 實作 shortcode 提取方法
  - 在 `downloader.py` 中實作 `_extract_shortcode_from_url` 方法
  - 支援多種 Instagram URL 格式（p/、reel/）
  - 使用正則表達式提取 shortcode
  - 加入 URL 格式驗證和錯誤處理
  - _需求：10.2, 10.5_

- [x] 17.2 實作單一貼文下載方法
  - 實作 `download_post_from_shortcode` 方法，使用 `Post.from_shortcode` API
  - 實作 `download_post_from_url` 方法，整合 URL 解析和貼文下載
  - 獲取貼文作者資訊並建立對應目錄
  - 返回 `DownloadStats` 統計資訊
  - _需求：10.1, 10.3, 10.4, 10.7, 10.8_

- [x] 17.3 處理單一貼文下載的錯誤
  - 處理 URL 格式錯誤（`ValueError`）
  - 處理貼文不存在錯誤
  - 處理私人貼文錯誤
  - 處理網路連線錯誤（重試機制）
  - _需求：10.5, 10.6_

- [x] 18. 實作批次 URL 下載功能
- [x] 18.1 實作 YAML 檔案讀取
  - 實作 `_read_urls_from_file` 方法，使用 `yaml.safe_load` 讀取檔案
  - 支援兩種 YAML 格式：簡化格式（URL 列表）和詳細格式（包含 description）
  - 加入 YAML 格式驗證和錯誤處理
  - 跳過無效的 URL 並記錄警告
  - _需求：10.1_

- [x] 18.2 實作批次下載方法
  - 實作 `download_posts_from_urls` 方法
  - 支援單執行緒和多執行緒兩種模式
  - 整合進度條顯示（使用 tqdm）
  - 收集並彙總所有貼文的統計資訊
  - _需求：10.1, 10.4_

- [x] 18.3 實作失敗重試機制
  - 在批次下載中加入重試邏輯（最多 3 次）
  - 實作遞增等待時間（2秒、4秒、6秒）
  - 記錄失敗的 URL 和錯誤原因
  - 實作 `_save_failed_urls` 方法，將失敗記錄儲存到 YAML 檔案
  - _需求：10.1_

- [x] 19. 實作進度條顯示功能
- [x] 19.1 整合 tqdm 到單執行緒下載
  - 在 `download_posts_from_urls` 中加入 tqdm 進度條
  - 顯示當前進度、成功數量、失敗數量
  - 顯示預估剩餘時間
  - _需求：10.1_

- [x] 19.2 整合 tqdm 到多執行緒下載
  - 在 `_download_posts_parallel` 中加入執行緒安全的 tqdm 進度條
  - 使用 `as_completed` 追蹤完成進度
  - 顯示下載速度（post/s）
  - 更新進度條的 postfix 資訊
  - _需求：10.1_

- [x] 19.3 實作詳細進度資訊
  - 計算並顯示下載速度
  - 顯示已下載的檔案數量和大小
  - 顯示預估剩餘時間
  - _需求：10.1_

- [x] 20. 更新命令列介面
- [x] 20.1 新增 URL 相關參數
  - 在 `parse_arguments` 中新增 `--url` 參數（與 username 互斥）
  - 新增 `--url-file` 參數（與 username、--url 互斥）
  - 實作參數互斥邏輯驗證
  - 更新 help 文字和使用範例
  - _需求：10.1_

- [x] 20.2 整合單一 URL 下載流程
  - 在 `main` 函數中加入 `--url` 參數的處理邏輯
  - 呼叫 `download_post_from_url` 方法
  - 顯示單一貼文的下載資訊
  - 顯示下載摘要
  - _需求：10.1, 10.8_

- [x] 20.3 整合批次 URL 下載流程
  - 在 `main` 函數中加入 `--url-file` 參數的處理邏輯
  - 讀取 YAML 檔案並獲取 URL 列表
  - 呼叫 `download_posts_from_urls` 方法
  - 顯示批次下載的摘要統計
  - 顯示失敗記錄檔案的位置（如果有失敗）
  - _需求：10.1_

- [x] 21. 更新使用文件
  - 在 `README.md` 中新增單一 URL 下載的使用範例
  - 新增批次 URL 下載的使用範例
  - 新增 YAML 檔案格式說明和範例
  - 新增失敗重試機制的說明
  - 新增進度條顯示的說明
  - _需求：10.1_

- [x] 22. 撰寫 URL 下載功能的測試
- [x] 22.1 撰寫 URL 解析測試
  - 測試 `_extract_shortcode_from_url` 方法
  - 測試各種 URL 格式（p/、reel/、http/https）
  - 測試無效 URL 的錯誤處理
  - _需求：10.2, 10.5_

- [x] 22.2 撰寫單一貼文下載測試
  - 使用 mock 測試 `download_post_from_url` 方法
  - 測試成功下載的情況
  - 測試各種錯誤情況（貼文不存在、私人貼文等）
  - _需求：10.1, 10.6_

- [x] 22.3 撰寫批次下載測試
  - 測試 `_read_urls_from_file` 方法（YAML 讀取）
  - 測試 `download_posts_from_urls` 方法
  - 測試失敗重試機制
  - 測試失敗記錄檔案的生成
  - _需求：10.1_

- [x] 22.4 撰寫進度條測試
  - 測試 tqdm 整合（使用 mock）
  - 測試進度資訊的更新
  - 測試多執行緒進度條
  - _需求：10.1_
