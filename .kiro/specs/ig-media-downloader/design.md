# 設計文件

## 概述

IG Media Downloader 是一個基於 Python 3.13 的命令列工具，使用 instaloader 套件來下載 Instagram 使用者的公開貼文媒體（圖片和影片）。系統採用模組化設計，將下載邏輯、檔案管理和錯誤處理分離，確保程式碼的可維護性和可擴展性。

## 架構

系統採用分層架構設計：

```
┌─────────────────────────────────┐
│     CLI Interface (main.py)     │  ← 使用者互動層
└────────────┬────────────────────┘
             │
┌────────────▼────────────────────┐
│   Downloader Service            │  ← 業務邏輯層
│   (downloader.py)               │
└────────────┬────────────────────┘
             │
┌────────────▼────────────────────┐
│   Instaloader Library           │  ← 第三方套件層
└─────────────────────────────────┘
             │
┌────────────▼────────────────────┐
│   File System                   │  ← 儲存層
└─────────────────────────────────┘
```

### 核心設計原則

1. **單一職責**：每個模組專注於特定功能
2. **錯誤隔離**：錯誤處理不影響其他貼文的下載
3. **進度透明**：即時反饋下載狀態
4. **資源管理**：適當處理檔案和網路資源

## 元件與介面

### 1. CLI Interface (`main.py`)

**職責**：處理命令列參數、初始化下載器、顯示結果

**介面**：
```python
def main() -> None:
    """主程式入口點"""
    
def parse_arguments() -> argparse.Namespace:
    """解析命令列參數"""
    
def display_summary(stats: DownloadStats) -> None:
    """顯示下載摘要"""
```

**參數**：
- `username` (選填)：目標 Instagram 帳號名稱（與 `--url`、`--url-file` 互斥）
- `--url` (選填)：Instagram 貼文 URL（與 `username`、`--url-file` 互斥）
- `--url-file` (選填)：包含多個 URL 的文字檔案路徑（與 `username`、`--url` 互斥）
- `--output-dir` (選填)：自訂下載目錄，預設為當前目錄
- `--max-posts` (選填)：限制下載的貼文數量（僅用於下載使用者）
- `--include-stories` (選填)：是否下載 Stories，預設為 False（僅用於下載使用者）
- `--include-reels` (選填)：是否下載 Reels，預設為 False（僅用於下載使用者）
- `--workers` (選填)：並行下載的執行緒數量，預設為 1（單執行緒）
- `--resume` (選填)：是否啟用斷點續傳，預設為 True

### 2. Downloader Service (`downloader.py`)

**職責**：封裝 instaloader 功能、管理下載流程、處理錯誤

**介面**：
```python
class IGDownloader:
    def __init__(self, output_dir: str = ".", max_workers: int = 1, resume: bool = True):
        """初始化下載器"""
        
    def download_user_media(
        self, 
        username: str, 
        max_posts: int | None = None,
        include_stories: bool = False,
        include_reels: bool = False
    ) -> DownloadStats:
        """下載指定使用者的媒體檔案"""
        
    def download_post_from_url(self, url: str) -> DownloadStats:
        """從 URL 下載單一貼文"""
        
    def download_post_from_shortcode(self, shortcode: str) -> DownloadStats:
        """從 shortcode 下載單一貼文"""
        
    def download_posts_from_urls(self, urls: list[str]) -> DownloadStats:
        """從多個 URL 批次下載貼文"""
        
    def download_stories(self, username: str) -> tuple[int, int]:
        """下載指定使用者的 Stories"""
        
    def download_reels(self, username: str) -> tuple[int, int]:
        """下載指定使用者的 Reels"""
        
    def _create_output_directory(self, username: str) -> Path:
        """建立輸出目錄"""
        
    def _download_post(self, post: Post) -> tuple[int, int]:
        """下載單一貼文的媒體"""
        
    def _download_posts_parallel(self, posts: list[Post]) -> list[tuple[int, int]]:
        """使用多執行緒並行下載貼文"""
        
    def _extract_shortcode_from_url(self, url: str) -> str:
        """從 URL 提取 shortcode"""
        
    def _is_already_downloaded(self, post: Post) -> bool:
        """檢查貼文是否已下載（斷點續傳）"""
        
    def _save_progress(self, username: str, downloaded_posts: set[str]) -> None:
        """儲存下載進度"""
        
    def _load_progress(self, username: str) -> set[str]:
        """載入下載進度"""
        
    def _handle_download_error(self, error: Exception, post_info: str) -> None:
        """處理下載錯誤"""
```

### 3. Data Models (`models.py`)

**職責**：定義資料結構

```python
@dataclass
class DownloadStats:
    """下載統計資訊"""
    username: str
    total_posts: int
    downloaded_images: int
    downloaded_videos: int
    skipped_files: int
    errors: int
    output_directory: str
    start_time: datetime
    end_time: datetime
    stories_downloaded: int = 0
    reels_downloaded: int = 0
    resumed_from_previous: bool = False
    
    @property
    def duration(self) -> timedelta:
        """計算下載耗時"""
        
    @property
    def total_files(self) -> int:
        """計算總下載檔案數"""
```

### 4. Logger (`logger.py`)

**職責**：統一的日誌管理

```python
def setup_logger(name: str, log_file: str = "ig_downloader.log") -> logging.Logger:
    """設定日誌記錄器"""
```

## 資料模型

### 檔案命名規則

下載的檔案將保留 instaloader 的預設命名格式：
```
{post_date}_{post_shortcode}_{media_index}.{extension}
```

例如：`2024-01-15_ABC123_1.jpg`

### 目錄結構

```
output_dir/
└── {username}/
    ├── posts/
    │   ├── 2024-01-15_ABC123_1.jpg
    │   ├── 2024-01-15_ABC123_2.jpg
    │   └── 2024-01-14_XYZ789_1.mp4
    ├── stories/
    │   ├── 2024-01-16_story_1.jpg
    │   └── 2024-01-16_story_2.mp4
    ├── reels/
    │   ├── 2024-01-15_reel_ABC123.mp4
    │   └── 2024-01-14_reel_XYZ789.mp4
    └── .download_progress.json
```

### 進度檔案格式

`.download_progress.json` 用於記錄已下載的貼文，支援斷點續傳：

```json
{
  "username": "example_user",
  "last_updated": "2024-01-16T10:30:00",
  "downloaded_posts": [
    "ABC123",
    "XYZ789"
  ],
  "downloaded_reels": [
    "REEL001"
  ]
}
```

## 錯誤處理

### 錯誤分類與處理策略

| 錯誤類型 | 處理策略 | 使用者反饋 |
|---------|---------|-----------|
| 帳號不存在 | 立即終止 | 顯示錯誤訊息並退出 |
| 網路連線失敗 | 重試 3 次 | 顯示重試進度 |
| 私人帳號 | 立即終止 | 提示需要登入 |
| 單一貼文失敗 | 記錄並繼續 | 記錄到日誌，繼續下一個 |
| 磁碟空間不足 | 立即終止 | 顯示錯誤並清理部分檔案 |
| 權限不足 | 立即終止 | 顯示權限錯誤訊息 |

### 錯誤處理流程

```python
try:
    # 下載操作
except ProfileNotExistsException:
    # 帳號不存在 - 終止
except ConnectionException:
    # 網路問題 - 重試
except PrivateProfileException:
    # 私人帳號 - 終止
except OSError as e:
    if e.errno == errno.ENOSPC:
        # 磁碟空間不足 - 終止
    elif e.errno == errno.EACCES:
        # 權限不足 - 終止
except Exception:
    # 其他錯誤 - 記錄並繼續
```

## 測試策略

### 單元測試

測試範圍：
- `IGDownloader` 類別的各個方法
- `DownloadStats` 資料模型的屬性計算
- 參數解析邏輯
- 錯誤處理邏輯

### 整合測試

測試場景：
- 下載公開帳號的媒體
- 處理不存在的帳號
- 處理網路錯誤
- 檔案系統錯誤處理

### 測試工具

- `pytest`：測試框架
- `pytest-mock`：模擬 instaloader 行為
- `pytest-cov`：程式碼覆蓋率

## 依賴管理

### pyproject.toml 配置

```toml
[project]
name = "ig-media-downloader"
version = "0.1.0"
description = "Download Instagram user media using instaloader"
requires-python = ">=3.13"
dependencies = [
    "instaloader>=4.10",
    "pyyaml>=6.0",
    "tqdm>=4.66",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4",
    "pytest-mock>=3.12",
    "pytest-cov>=4.1",
]

[project.scripts]
ig-download = "ig_media_downloader.main:main"
```

### 安裝與執行

```bash
# 使用 uv 安裝依賴
uv pip install -e .

# 執行下載
ig-download <username>

# 或直接執行
python -m ig_media_downloader.main <username>
```

## 效能考量

1. **批次處理**：一次處理一個貼文，避免記憶體溢出
2. **檔案檢查**：下載前檢查檔案是否已存在，避免重複下載
3. **連線管理**：重用 instaloader 的連線池
4. **進度顯示**：使用 tqdm 顯示下載進度條，提供即時反饋
5. **多執行緒下載**：使用 `concurrent.futures.ThreadPoolExecutor` 實現並行下載
   - 預設單執行緒，避免對 Instagram 伺服器造成過大負擔
   - 可透過 `--workers` 參數調整執行緒數量（建議不超過 4）
   - 使用執行緒鎖保護共享資源（統計資料、日誌）
6. **Stories 時效性**：Stories 有 24 小時時效，優先下載 Stories 再下載貼文

## 進度條顯示實作

### 使用 tqdm 顯示進度

```python
from tqdm import tqdm

def download_posts_from_urls(self, urls: list[str]) -> DownloadStats:
    """從多個 URL 批次下載貼文，顯示進度條"""
    
    # 建立進度條
    with tqdm(total=len(urls), desc="下載貼文", unit="post") as pbar:
        for url in urls:
            try:
                stats = self.download_post_from_url(url)
                pbar.set_postfix({
                    '成功': f"{downloaded_images + downloaded_videos}",
                    '失敗': f"{errors}"
                })
            except Exception as e:
                errors += 1
            finally:
                pbar.update(1)
```

### 進度條顯示效果

基本進度條：
```
下載貼文: 45%|████████████▌              | 9/20 [00:15<00:18, 1.68s/post] 成功: 8, 失敗: 1
```

詳細進度資訊（包含下載速度和剩餘時間）：
```
下載貼文: 45%|████████████▌              | 9/20 [00:15<00:18, 1.68s/post]
  ├─ 成功: 8 個 | 失敗: 1 個
  ├─ 下載速度: 2.5 MB/s
  └─ 預計剩餘: 18 秒
```

### 多執行緒進度條

對於多執行緒下載，使用 tqdm 的執行緒安全模式：

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import time

def _download_posts_parallel(self, posts: list[Post]) -> list[tuple[int, int]]:
    """使用多執行緒並行下載，顯示進度條"""
    results = []
    start_time = time.time()
    total_bytes = 0
    
    with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
        # 提交所有任務
        future_to_post = {
            executor.submit(self._download_post, post): post 
            for post in posts
        }
        
        # 使用 tqdm 追蹤完成進度
        with tqdm(
            total=len(posts), 
            desc="並行下載", 
            unit="post",
            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]'
        ) as pbar:
            for future in as_completed(future_to_post):
                try:
                    result = future.result()
                    results.append(result)
                    
                    # 計算下載速度（假設每個貼文平均大小）
                    elapsed = time.time() - start_time
                    if elapsed > 0:
                        speed = len(results) / elapsed
                        pbar.set_postfix({
                            '成功': len([r for r in results if r != (0, 0, 0)]),
                            '速度': f'{speed:.2f} post/s'
                        })
                except Exception as e:
                    results.append((0, 0, 0))
                finally:
                    pbar.update(1)
    
    return results
```

### 詳細進度資訊實作

對於需要顯示下載速度和檔案大小的場景：

```python
from tqdm import tqdm
import os

def download_post_from_url(self, url: str, show_progress: bool = True) -> DownloadStats:
    """從 URL 下載單一貼文，顯示詳細進度"""
    
    if show_progress:
        # 建立進度條，追蹤檔案下載
        with tqdm(
            desc="下載媒體",
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
        ) as pbar:
            # 下載過程中更新進度條
            # instaloader 內部處理下載，我們在外層顯示整體進度
            stats = self._download_with_progress(url, pbar)
    else:
        stats = self._download_post_internal(url)
    
    return stats

def _download_with_progress(self, url: str, pbar: tqdm) -> DownloadStats:
    """下載並更新進度條"""
    # 實作下載邏輯
    # 每下載一個檔案就更新進度條
    pass
```

## 安全性考量

1. **不儲存密碼**：本版本僅支援公開帳號，不處理登入
2. **路徑驗證**：驗證輸出路徑，防止路徑遍歷攻擊
3. **錯誤訊息**：不在錯誤訊息中洩露敏感資訊
4. **速率限制**：遵守 Instagram 的 API 速率限制（由 instaloader 處理）

## 多執行緒實作細節

### 執行緒池設計

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

class IGDownloader:
    def __init__(self, output_dir: str = ".", max_workers: int = 1):
        self.max_workers = max_workers
        self.stats_lock = Lock()  # 保護統計資料
        
    def _download_posts_parallel(self, posts: list[Post]) -> list[tuple[int, int]]:
        """使用執行緒池並行下載"""
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_post = {
                executor.submit(self._download_post, post): post 
                for post in posts
            }
            for future in as_completed(future_to_post):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    # 錯誤處理
                    pass
        return results
```

### 執行緒安全考量

1. **統計資料更新**：使用 `threading.Lock` 保護 `DownloadStats` 的更新
2. **日誌記錄**：Python 的 `logging` 模組本身是執行緒安全的
3. **檔案寫入**：instaloader 內部處理檔案寫入的執行緒安全
4. **速率限制**：避免過多並行請求導致被 Instagram 封鎖

## Stories 下載實作

### Stories 特性

- Stories 在發布後 24 小時內有效
- 需要即時下載，否則會失效
- Stories 可能包含圖片或影片

### 實作方式

```python
def download_stories(self, username: str) -> tuple[int, int]:
    """下載 Stories"""
    loader = instaloader.Instaloader(dirname_pattern=f"{username}/stories")
    profile = instaloader.Profile.from_username(loader.context, username)
    
    images = 0
    videos = 0
    
    for story in loader.get_stories(userids=[profile.userid]):
        for item in story.get_items():
            loader.download_storyitem(item, f"{username}/stories")
            if item.is_video:
                videos += 1
            else:
                images += 1
                
    return images, videos
```

## Reels 下載實作

### Reels 特性

- Reels 是 Instagram 的短影片功能
- Reels 可以在使用者的個人檔案中找到
- 需要特別的 API 呼叫來獲取 Reels

### 實作方式

```python
def download_reels(self, username: str) -> tuple[int, int]:
    """下載 Reels"""
    loader = instaloader.Instaloader(dirname_pattern=f"{username}/reels")
    profile = instaloader.Profile.from_username(loader.context, username)
    
    videos = 0
    
    for post in profile.get_posts():
        if post.is_video and post.typename == 'GraphVideo':
            # 檢查是否為 Reel
            if self._is_reel(post):
                loader.download_post(post, target=f"{username}/reels")
                videos += 1
                
    return 0, videos  # Reels 只有影片
    
def _is_reel(self, post: Post) -> bool:
    """判斷貼文是否為 Reel"""
    # 透過貼文的 product_type 或其他屬性判斷
    return hasattr(post, 'product_type') and post.product_type == 'clips'
```

## 斷點續傳實作

### 設計原理

1. **進度追蹤**：使用 JSON 檔案記錄已下載的貼文 shortcode
2. **檢查機制**：下載前檢查貼文是否已在進度檔案中
3. **定期儲存**：每下載完一個貼文就更新進度檔案
4. **容錯處理**：進度檔案損壞時從頭開始

### 實作細節

```python
import json
from pathlib import Path

class IGDownloader:
    def _load_progress(self, username: str) -> set[str]:
        """載入下載進度"""
        progress_file = Path(self.output_dir) / username / ".download_progress.json"
        if not progress_file.exists():
            return set()
            
        try:
            with open(progress_file, 'r') as f:
                data = json.load(f)
                return set(data.get('downloaded_posts', []))
        except (json.JSONDecodeError, IOError):
            # 進度檔案損壞，從頭開始
            return set()
    
    def _save_progress(self, username: str, downloaded_posts: set[str]) -> None:
        """儲存下載進度"""
        progress_file = Path(self.output_dir) / username / ".download_progress.json"
        progress_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'username': username,
            'last_updated': datetime.now().isoformat(),
            'downloaded_posts': list(downloaded_posts)
        }
        
        with open(progress_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _is_already_downloaded(self, post: Post) -> bool:
        """檢查貼文是否已下載"""
        return post.shortcode in self.downloaded_posts
```

### 使用流程

1. 程式啟動時載入進度檔案
2. 遍歷貼文時跳過已下載的項目
3. 每下載完一個貼文就更新進度檔案
4. 下載中斷後重新執行，會從上次中斷處繼續

## 單一貼文下載實作

### URL 格式支援

Instagram 貼文 URL 的常見格式：
- `https://www.instagram.com/p/{shortcode}/`
- `https://instagram.com/p/{shortcode}/`
- `http://www.instagram.com/p/{shortcode}/`
- `https://www.instagram.com/reel/{shortcode}/` (Reels)

### Shortcode 提取

```python
import re
from urllib.parse import urlparse

def _extract_shortcode_from_url(self, url: str) -> str:
    """從 URL 提取 shortcode"""
    # 支援的 URL 格式：
    # https://www.instagram.com/p/ABC123/
    # https://www.instagram.com/reel/ABC123/
    
    pattern = r'instagram\.com/(?:p|reel)/([A-Za-z0-9_-]+)'
    match = re.search(pattern, url)
    
    if not match:
        raise ValueError(f"無效的 Instagram URL 格式: {url}")
    
    return match.group(1)
```

### 單一貼文下載流程

```python
def download_post_from_url(self, url: str) -> DownloadStats:
    """從 URL 下載單一貼文"""
    start_time = datetime.now()
    
    try:
        # 1. 從 URL 提取 shortcode
        shortcode = self._extract_shortcode_from_url(url)
        
        # 2. 使用 shortcode 獲取貼文物件
        post = instaloader.Post.from_shortcode(self.loader.context, shortcode)
        
        # 3. 建立輸出目錄（使用貼文作者的使用者名稱）
        username = post.owner_username
        self._create_output_directory(username)
        
        # 4. 下載貼文
        images, videos, skipped = self._download_post(post, username)
        
        # 5. 建立統計資訊
        end_time = datetime.now()
        stats = DownloadStats(
            username=username,
            total_posts=1,
            downloaded_images=images,
            downloaded_videos=videos,
            skipped_files=skipped,
            errors=0,
            output_directory=str(self.output_dir / username),
            start_time=start_time,
            end_time=end_time,
        )
        
        return stats
        
    except ValueError as e:
        # URL 格式錯誤
        self.logger.error(f"URL 格式錯誤: {e}")
        raise
    except Exception as e:
        # 其他錯誤
        self.logger.error(f"下載貼文失敗: {e}")
        raise
```

### 目錄結構（單一貼文）

下載單一貼文時，檔案會儲存在以貼文作者命名的目錄中：

```
output_dir/
└── {post_owner_username}/
    └── posts/
        ├── 2024-01-15_ABC123_1.jpg
        └── 2024-01-15_ABC123_2.jpg
```

### CLI 使用範例

```bash
# 下載單一貼文
ig-download --url https://www.instagram.com/p/ABC123xyz/

# 指定輸出目錄
ig-download --url https://www.instagram.com/p/ABC123xyz/ --output-dir ~/Downloads

# 下載 Reel
ig-download --url https://www.instagram.com/reel/XYZ789abc/

# 從 YAML 檔案批次下載多個 URL
ig-download --url-file urls.yaml

# 使用多執行緒批次下載
ig-download --url-file urls.yaml --workers 4
```

### 錯誤處理

| 錯誤情況 | 處理方式 |
|---------|---------|
| URL 格式不正確 | 拋出 `ValueError`，顯示錯誤訊息 |
| Shortcode 無效 | 拋出 `PostNotExistsException` |
| 貼文不存在 | 拋出 `PostNotExistsException` |
| 貼文為私人 | 拋出 `PrivateProfileNotFollowedException` |
| 網路連線失敗 | 重試 3 次，失敗後拋出 `ConnectionException` |

## 批次 URL 下載實作

### URL 檔案格式

URL 檔案使用 YAML 格式，支援更豐富的配置選項：

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

### 批次下載流程

```python
def download_posts_from_urls(self, urls: list[str]) -> DownloadStats:
    """從多個 URL 批次下載貼文"""
    start_time = datetime.now()
    
    total_posts = len(urls)
    downloaded_images = 0
    downloaded_videos = 0
    skipped_files = 0
    errors = 0
    
    # 使用多執行緒或單執行緒下載
    if self.max_workers == 1:
        # 單執行緒模式
        for url in urls:
            try:
                stats = self.download_post_from_url(url)
                downloaded_images += stats.downloaded_images
                downloaded_videos += stats.downloaded_videos
                skipped_files += stats.skipped_files
            except Exception as e:
                self.logger.error(f"下載失敗: {url} - {e}")
                errors += 1
    else:
        # 多執行緒模式
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {
                executor.submit(self.download_post_from_url, url): url 
                for url in urls
            }
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    stats = future.result()
                    with self.stats_lock:
                        downloaded_images += stats.downloaded_images
                        downloaded_videos += stats.downloaded_videos
                        skipped_files += stats.skipped_files
                except Exception as e:
                    self.logger.error(f"下載失敗: {url} - {e}")
                    with self.stats_lock:
                        errors += 1
    
    end_time = datetime.now()
    
    return DownloadStats(
        username="batch_download",
        total_posts=total_posts,
        downloaded_images=downloaded_images,
        downloaded_videos=downloaded_videos,
        skipped_files=skipped_files,
        errors=errors,
        output_directory=str(self.output_dir),
        start_time=start_time,
        end_time=end_time,
    )
```

### URL 檔案讀取

```python
import yaml

def _read_urls_from_file(file_path: str) -> list[str]:
    """從 YAML 檔案讀取 URL 列表"""
    urls = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if not data or 'urls' not in data:
            raise ValueError("YAML 檔案格式錯誤：缺少 'urls' 欄位")
        
        url_list = data['urls']
        
        for item in url_list:
            # 支援兩種格式：
            # 1. 字串格式：直接是 URL
            # 2. 字典格式：包含 url 和 description
            if isinstance(item, str):
                url = item
            elif isinstance(item, dict) and 'url' in item:
                url = item['url']
            else:
                logger.warning(f"跳過無效的項目: {item}")
                continue
            
            # 驗證 URL 格式
            if 'instagram.com' in url:
                urls.append(url)
            else:
                logger.warning(f"跳過無效的 URL: {url}")
        
        return urls
        
    except yaml.YAMLError as e:
        raise ValueError(f"YAML 檔案解析錯誤: {e}")
    except FileNotFoundError:
        raise FileNotFoundError(f"找不到檔案: {file_path}")
```

### 錯誤處理與重試機制

批次下載時的錯誤處理：
- 單一 URL 下載失敗不影響其他 URL
- 記錄所有失敗的 URL 和錯誤原因
- 在摘要中顯示成功和失敗的數量
- 失敗的 URL 自動記錄到失敗檔案

#### 失敗重試機制

```python
def download_posts_from_urls(self, urls: list[str], max_retries: int = 3) -> DownloadStats:
    """從多個 URL 批次下載貼文，支援失敗重試"""
    failed_urls = []  # 記錄失敗的 URL
    
    for url in urls:
        success = False
        last_error = None
        
        # 重試機制
        for attempt in range(max_retries):
            try:
                stats = self.download_post_from_url(url)
                success = True
                break
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2  # 2秒、4秒、6秒
                    self.logger.warning(
                        f"下載失敗 (嘗試 {attempt + 1}/{max_retries}): {url} - {e}"
                        f"，{wait_time} 秒後重試"
                    )
                    time.sleep(wait_time)
        
        # 記錄失敗的 URL
        if not success:
            failed_urls.append({
                'url': url,
                'error': str(last_error),
                'timestamp': datetime.now().isoformat()
            })
            self.logger.error(f"下載失敗（已重試 {max_retries} 次）: {url} - {last_error}")
    
    # 儲存失敗的 URL 到檔案
    if failed_urls:
        self._save_failed_urls(failed_urls)
    
    return stats
```

#### 失敗記錄檔案格式

失敗的 URL 會記錄到 `failed_downloads.yaml`：

```yaml
# failed_downloads.yaml
failed_downloads:
  - url: https://www.instagram.com/p/ABC123xyz/
    error: "ConnectionException: Network timeout"
    timestamp: "2024-01-16T15:30:00"
    
  - url: https://www.instagram.com/p/DEF456uvw/
    error: "PostNotExistsException: Post not found"
    timestamp: "2024-01-16T15:31:00"
```

#### 失敗檔案儲存

```python
def _save_failed_urls(self, failed_urls: list[dict]) -> None:
    """儲存失敗的 URL 到 YAML 檔案"""
    failed_file = self.output_dir / "failed_downloads.yaml"
    
    data = {'failed_downloads': failed_urls}
    
    try:
        with open(failed_file, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
        
        self.logger.info(f"失敗的 URL 已記錄到: {failed_file}")
    except Exception as e:
        self.logger.error(f"無法儲存失敗記錄: {e}")
```

## 未來擴展

可能的功能擴展：
1. 支援登入以下載私人帳號
2. 提供 GUI 介面
3. 支援下載 Highlights
4. 支援下載留言和按讚資訊
5. 支援批次下載多個帳號
6. 支援從剪貼簿讀取 URL
7. 支援從失敗記錄檔案重新下載
8. 支援更詳細的進度資訊（下載速度、剩餘時間等）
