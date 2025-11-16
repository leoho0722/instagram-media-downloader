"""核心下載器模組 - 封裝 instaloader 功能並管理下載流程。"""

import errno
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from threading import Lock

import instaloader
import yaml
from instaloader.exceptions import (
    ConnectionException,
    ProfileNotExistsException,
    PrivateProfileNotFollowedException,
)
from tqdm import tqdm

from .logger import setup_logger
from .models import DownloadStats


class IGDownloader:
    """Instagram 媒體下載器類別。

    負責管理下載流程、處理錯誤、支援多執行緒和斷點續傳。
    """

    def __init__(
        self, output_dir: str = ".", max_workers: int = 1, resume: bool = True
    ) -> None:
        """初始化下載器。

        Args:
            output_dir: 下載檔案的輸出目錄，預設為當前目錄
            max_workers: 並行下載的執行緒數量，預設為 1（單執行緒）
            resume: 是否啟用斷點續傳，預設為 True

        需求：
            - 7.1: WHERE 使用者指定執行緒數量，THE IG Downloader SHALL 使用指定數量的執行緒進行並行下載
            - 7.2: THE IG Downloader SHALL 預設使用單執行緒模式以避免對伺服器造成過大負擔
            - 9.1: THE IG Downloader SHALL 預設啟用斷點續傳功能
        """
        self.output_dir = Path(output_dir)
        self.max_workers = min(max_workers, 8)  # 限制最大執行緒數量為 8
        self.resume = resume
        self.logger = setup_logger(__name__)

        # 初始化 instaloader
        self.loader = instaloader.Instaloader(
            download_comments=False,
            download_geotags=False,
            download_video_thumbnails=False,
            compress_json=False,
            save_metadata=False,
        )

        # 執行緒鎖，用於保護統計資料更新
        self.stats_lock = Lock()

        # 已下載的貼文集合（用於斷點續傳）
        self.downloaded_posts: set[str] = set()

        self.logger.info(
            f"IGDownloader 初始化完成 - 輸出目錄: {self.output_dir}, "
            f"執行緒數: {self.max_workers}, 斷點續傳: {self.resume}"
        )

    def _create_output_directory(self, username: str) -> Path:
        """建立使用者專屬的輸出目錄結構。

        Args:
            username: Instagram 使用者名稱

        Returns:
            建立的目錄路徑

        需求：
            - 2.1: THE IG Downloader SHALL 建立一個以目標帳號名稱命名的下載目錄
            - 2.2: WHEN 下載目錄不存在時，THE IG Downloader SHALL 自動建立該目錄
        """
        user_dir = self.output_dir / username
        posts_dir = user_dir / "posts"

        try:
            # 建立主目錄和子目錄
            posts_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"建立輸出目錄: {user_dir}")
            return user_dir

        except OSError as e:
            if e.errno == errno.EACCES:
                # 權限不足
                self.logger.error(f"權限不足，無法建立目錄: {user_dir}")
                raise PermissionError(f"無法建立目錄 {user_dir}，請檢查檔案權限") from e
            elif e.errno == errno.ENOSPC:
                # 磁碟空間不足
                self.logger.error(f"磁碟空間不足，無法建立目錄: {user_dir}")
                raise OSError("磁碟空間不足，無法建立目錄") from e
            else:
                self.logger.error(f"建立目錄時發生錯誤: {e}")
                raise

    def _retry_on_connection_error(self, func, *args, max_retries: int = 3, **kwargs):
        """在網路連線錯誤時重試操作。

        此方法會在發生 ConnectionException 時自動重試，最多重試 3 次。
        每次重試之間會有遞增的等待時間（1秒、2秒、3秒）。

        Args:
            func: 要執行的函數
            *args: 函數的位置參數
            max_retries: 最大重試次數，預設為 3
            **kwargs: 函數的關鍵字參數

        Returns:
            函數的返回值

        Raises:
            ConnectionException: 當重試次數用盡後仍然失敗時

        需求：
            - 4.1: IF 網路連線失敗，THEN THE IG Downloader SHALL 顯示網路錯誤訊息並提供重試選項
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)

            except ConnectionException as e:
                last_error = e
                if attempt < max_retries - 1:
                    # 還有重試機會
                    wait_time = attempt + 1  # 1秒、2秒、3秒
                    self.logger.warning(
                        f"網路連線失敗 (嘗試 {attempt + 1}/{max_retries})，"
                        f"{wait_time} 秒後重試: {e}"
                    )
                    time.sleep(wait_time)
                else:
                    # 重試次數用盡
                    self.logger.error(
                        f"網路連線失敗，已重試 {max_retries} 次，放棄操作: {e}"
                    )
                    raise e

        # 理論上不會執行到這裡，但為了安全起見
        if last_error:
            raise last_error

    def _handle_download_error(self, error: Exception, context: str = "") -> None:
        """處理下載過程中的錯誤。

        根據錯誤類型採取不同的處理策略：
        - 帳號不存在：記錄錯誤並重新拋出
        - 網路錯誤：記錄錯誤並重新拋出（由呼叫者處理重試）
        - 私人帳號：記錄錯誤並重新拋出
        - 磁碟空間不足：記錄錯誤並重新拋出
        - 其他錯誤：記錄錯誤但不中斷執行

        Args:
            error: 捕獲的異常
            context: 錯誤發生的上下文資訊（例如：貼文 ID、使用者名稱等）

        需求：
            - 1.3: IF 提供的帳號名稱不存在，THEN THE IG Downloader SHALL 顯示錯誤訊息並終止執行
            - 4.1: IF 網路連線失敗，THEN THE IG Downloader SHALL 顯示網路錯誤訊息並提供重試選項
            - 4.2: IF Instagram API 回應錯誤，THEN THE IG Downloader SHALL 記錄錯誤詳情並繼續處理其他貼文
            - 4.3: IF 磁碟空間不足，THEN THE IG Downloader SHALL 顯示警告訊息並停止下載
            - 4.4: IF 檔案寫入權限不足，THEN THE IG Downloader SHALL 顯示權限錯誤訊息並終止執行
            - 4.5: THE IG Downloader SHALL 記錄所有錯誤到日誌檔案中以供除錯使用
        """
        context_msg = f" ({context})" if context else ""

        if isinstance(error, ProfileNotExistsException):
            # 帳號不存在 - 嚴重錯誤，需要終止
            self.logger.error(f"帳號不存在{context_msg}: {error}")
            raise error

        elif isinstance(error, ConnectionException):
            # 網路連線錯誤 - 嚴重錯誤，但可以重試
            self.logger.error(f"網路連線失敗{context_msg}: {error}")
            raise error

        elif isinstance(error, PrivateProfileNotFollowedException):
            # 私人帳號 - 嚴重錯誤，需要終止
            self.logger.error(f"私人帳號，需要登入{context_msg}: {error}")
            raise error

        elif isinstance(error, OSError):
            if error.errno == errno.ENOSPC:
                # 磁碟空間不足 - 嚴重錯誤，需要終止
                self.logger.error(f"磁碟空間不足{context_msg}")
                raise error
            elif error.errno == errno.EACCES:
                # 權限不足 - 嚴重錯誤，需要終止
                self.logger.error(f"檔案權限不足{context_msg}")
                raise error
            else:
                # 其他檔案系統錯誤 - 記錄但繼續
                self.logger.warning(f"檔案系統錯誤{context_msg}: {error}")

        else:
            # 其他未預期的錯誤 - 記錄但繼續處理
            self.logger.warning(
                f"下載過程中發生錯誤{context_msg}: {type(error).__name__} - {error}"
            )

    def _load_progress(self, username: str) -> set[str]:
        """從 JSON 檔案載入下載進度。

        Args:
            username: Instagram 使用者名稱

        Returns:
            已下載的貼文 shortcode 集合

        需求：
            - 9.2: THE IG Downloader SHALL 在下載目錄中建立進度記錄檔案
            - 9.3: WHEN 開始下載時，THE IG Downloader SHALL 載入先前的下載進度
            - 9.6: IF 進度記錄檔案損壞或無法讀取，THEN THE IG Downloader SHALL 從頭開始下載
        """
        progress_file = self.output_dir / username / ".download_progress.json"

        # 如果進度檔案不存在，返回空集合
        if not progress_file.exists():
            self.logger.info("未找到進度檔案，將從頭開始下載")
            return set()

        try:
            with open(progress_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 驗證資料格式
            if not isinstance(data, dict):
                self.logger.warning("進度檔案格式錯誤，將從頭開始下載")
                return set()

            downloaded_posts = data.get("downloaded_posts", [])
            downloaded_reels = data.get("downloaded_reels", [])

            # 合併貼文和 Reels 的 shortcode
            all_downloaded = set(downloaded_posts) | set(downloaded_reels)

            self.logger.info(f"載入進度檔案成功 - 已下載 {len(all_downloaded)} 個項目")
            return all_downloaded

        except json.JSONDecodeError as e:
            # JSON 解析錯誤 - 檔案損壞
            self.logger.warning(f"進度檔案損壞，無法解析 JSON: {e}，將從頭開始下載")
            return set()

        except (IOError, OSError) as e:
            # 檔案讀取錯誤
            self.logger.warning(f"無法讀取進度檔案: {e}，將從頭開始下載")
            return set()

        except Exception as e:
            # 其他未預期的錯誤
            self.logger.warning(f"載入進度檔案時發生未預期的錯誤: {e}，將從頭開始下載")
            return set()

    def _save_progress(self, username: str, downloaded_posts: set[str]) -> None:
        """儲存下載進度到 JSON 檔案。

        Args:
            username: Instagram 使用者名稱
            downloaded_posts: 已下載的貼文 shortcode 集合

        需求：
            - 9.2: THE IG Downloader SHALL 在下載目錄中建立進度記錄檔案
            - 9.5: THE IG Downloader SHALL 在每個貼文下載完成後立即更新進度記錄
        """
        progress_file = self.output_dir / username / ".download_progress.json"

        try:
            # 確保目錄存在
            progress_file.parent.mkdir(parents=True, exist_ok=True)

            # 準備進度資料
            data = {
                "username": username,
                "last_updated": datetime.now().isoformat(),
                "downloaded_posts": sorted(list(downloaded_posts)),
                "downloaded_reels": [],  # 預留給未來的 Reels 功能
            }

            # 寫入 JSON 檔案
            with open(progress_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self.logger.debug(f"進度檔案已更新 - 共 {len(downloaded_posts)} 個項目")

        except (IOError, OSError) as e:
            # 檔案寫入錯誤 - 記錄警告但不中斷執行
            self.logger.warning(f"無法儲存進度檔案: {e}")

        except Exception as e:
            # 其他未預期的錯誤
            self.logger.warning(f"儲存進度檔案時發生未預期的錯誤: {e}")

    def _is_already_downloaded(self, post_shortcode: str) -> bool:
        """檢查貼文是否已下載（用於斷點續傳）。

        Args:
            post_shortcode: 貼文的 shortcode（唯一識別碼）

        Returns:
            True 如果貼文已下載，False 否則

        需求：
            - 9.4: THE IG Downloader SHALL 跳過已下載的貼文和媒體檔案
        """
        return post_shortcode in self.downloaded_posts

    def _download_post(self, post, username: str) -> tuple[int, int, int]:
        """下載單一貼文的圖片和影片。

        Args:
            post: instaloader.Post 物件
            username: Instagram 使用者名稱

        Returns:
            tuple[int, int, int]: (下載的圖片數, 下載的影片數, 跳過的檔案數)

        需求：
            - 1.1: THE IG Downloader SHALL 接受一個 Instagram 帳號名稱作為輸入參數
            - 1.2: WHEN 使用者提供有效的帳號名稱時，THE IG Downloader SHALL 連接到 Instagram 並擷取該帳號的貼文資訊
            - 1.4: THE IG Downloader SHALL 下載目標帳號中所有可存取的圖片檔案
            - 1.5: THE IG Downloader SHALL 下載目標帳號中所有可存取的影片檔案
            - 2.3: THE IG Downloader SHALL 將每個媒體檔案儲存到對應的下載目錄中
            - 2.4: THE IG Downloader SHALL 保留媒體檔案的原始檔名或使用有意義的命名規則
            - 9.4: THE IG Downloader SHALL 跳過已下載的貼文和媒體檔案
        """
        images_count = 0
        videos_count = 0
        skipped_count = 0

        try:
            # 檢查是否已下載（斷點續傳）
            if self.resume and self._is_already_downloaded(post.shortcode):
                self.logger.info(
                    f"跳過已下載的貼文: {post.shortcode} "
                    f"(日期: {post.date_local.strftime('%Y-%m-%d')})"
                )
                # 返回 0, 0, 1 表示跳過了這個貼文
                return 0, 0, 1

            # 設定下載目標目錄
            target_dir = self.output_dir / username / "posts"

            # 檢查檔案是否已存在（避免重複下載）
            # instaloader 會使用格式：YYYY-MM-DD_HH-MM-SS_UTC_shortcode
            # 檢查是否有任何以此 shortcode 開頭的檔案
            existing_files = list(target_dir.glob(f"*{post.shortcode}*"))
            if existing_files:
                self.logger.info(
                    f"檔案已存在，跳過貼文: {post.shortcode} "
                    f"(找到 {len(existing_files)} 個檔案)"
                )
                skipped_count = len(existing_files)
                return 0, 0, skipped_count

            # 記錄下載開始
            self.logger.info(
                f"開始下載貼文: {post.shortcode} "
                f"(日期: {post.date_local.strftime('%Y-%m-%d')}, "
                f"類型: {'影片' if post.is_video else '圖片'})"
            )

            # 使用 instaloader 下載貼文
            # 設定目標目錄為 posts 子目錄
            self.loader.dirname_pattern = str(target_dir)
            self.loader.download_post(post, target=username)

            # 統計下載的檔案
            if post.is_video:
                videos_count = 1
                self.logger.info(f"成功下載影片: {post.shortcode}")
            else:
                # 對於圖片貼文，可能包含多張圖片（輪播貼文）
                if post.typename == "GraphSidecar":
                    # 輪播貼文，計算圖片數量
                    images_count = len(list(post.get_sidecar_nodes()))
                    self.logger.info(
                        f"成功下載輪播貼文: {post.shortcode} ({images_count} 張圖片)"
                    )
                else:
                    # 單張圖片
                    images_count = 1
                    self.logger.info(f"成功下載圖片: {post.shortcode}")

            # 更新已下載集合（用於斷點續傳）
            if self.resume:
                with self.stats_lock:
                    self.downloaded_posts.add(post.shortcode)
                    # 立即儲存進度
                    self._save_progress(username, self.downloaded_posts)

            return images_count, videos_count, skipped_count

        except ConnectionException as e:
            # 網路連線錯誤 - 記錄並重新拋出
            self.logger.error(f"下載貼文 {post.shortcode} 時網路連線失敗: {e}")
            raise

        except OSError as e:
            if e.errno == errno.ENOSPC:
                # 磁碟空間不足 - 嚴重錯誤
                self.logger.error(f"磁碟空間不足，無法下載貼文 {post.shortcode}")
                raise
            elif e.errno == errno.EACCES:
                # 權限不足 - 嚴重錯誤
                self.logger.error(f"檔案權限不足，無法下載貼文 {post.shortcode}")
                raise
            else:
                # 其他檔案系統錯誤 - 記錄但不中斷
                self.logger.warning(
                    f"下載貼文 {post.shortcode} 時發生檔案系統錯誤: {e}"
                )
                return 0, 0, 0

        except Exception as e:
            # 其他未預期的錯誤 - 記錄但不中斷整個下載流程
            self.logger.warning(
                f"下載貼文 {post.shortcode} 時發生錯誤: {type(e).__name__} - {e}"
            )
            return 0, 0, 0

    def _download_posts_parallel(
        self, posts: list, username: str
    ) -> list[tuple[int, int, int]]:
        """使用多執行緒並行下載貼文。

        此方法使用 ThreadPoolExecutor 來並行下載多個貼文，
        提高下載效率。執行緒數量由初始化時的 max_workers 參數控制。

        Args:
            posts: instaloader.Post 物件列表
            username: Instagram 使用者名稱

        Returns:
            list[tuple[int, int, int]]: 每個貼文的下載結果列表
            每個元組包含 (下載的圖片數, 下載的影片數, 跳過的檔案數)

        需求：
            - 7.1: WHERE 使用者指定執行緒數量，THE IG Downloader SHALL 使用指定數量的執行緒進行並行下載
            - 7.3: THE IG Downloader SHALL 限制最大執行緒數量不超過 8 個
            - 7.4: WHILE 多執行緒下載進行中，THE IG Downloader SHALL 確保統計資料更新的執行緒安全性
            - 7.5: IF 任一執行緒發生錯誤，THEN THE IG Downloader SHALL 記錄錯誤並繼續其他執行緒的下載作業
        """
        results = []

        # 如果只有一個執行緒，直接循序下載
        if self.max_workers == 1:
            self.logger.info("使用單執行緒模式下載貼文")
            for post in posts:
                try:
                    result = self._download_post(post, username)
                    results.append(result)
                except Exception as e:
                    # 錯誤已在 _download_post 中處理，這裡只記錄
                    self.logger.error(
                        f"下載貼文 {post.shortcode} 時發生嚴重錯誤: {type(e).__name__} - {e}"
                    )
                    # 如果是嚴重錯誤（網路、磁碟空間等），重新拋出
                    if isinstance(
                        e,
                        (
                            ConnectionException,
                            OSError,
                            ProfileNotExistsException,
                            PrivateProfileNotFollowedException,
                        ),
                    ):
                        raise
                    # 其他錯誤則繼續處理下一個貼文
                    results.append((0, 0, 0))
            return results

        # 多執行緒模式
        self.logger.info(f"使用 {self.max_workers} 個執行緒並行下載貼文")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有下載任務
            future_to_post = {
                executor.submit(self._download_post, post, username): post
                for post in posts
            }

            # 處理完成的任務
            for future in as_completed(future_to_post):
                post = future_to_post[future]
                try:
                    # 獲取下載結果
                    result = future.result()
                    results.append(result)

                except ConnectionException as e:
                    # 網路連線錯誤 - 嚴重錯誤，停止所有下載
                    self.logger.error(
                        f"執行緒中發生網路連線錯誤 (貼文: {post.shortcode}): {e}"
                    )
                    # 取消所有待處理的任務
                    for f in future_to_post:
                        f.cancel()
                    raise

                except OSError as e:
                    if e.errno in (errno.ENOSPC, errno.EACCES):
                        # 磁碟空間不足或權限不足 - 嚴重錯誤，停止所有下載
                        self.logger.error(
                            f"執行緒中發生嚴重錯誤 (貼文: {post.shortcode}): {e}"
                        )
                        # 取消所有待處理的任務
                        for f in future_to_post:
                            f.cancel()
                        raise
                    else:
                        # 其他檔案系統錯誤 - 記錄但繼續
                        self.logger.warning(
                            f"執行緒中發生檔案系統錯誤 (貼文: {post.shortcode}): {e}"
                        )
                        results.append((0, 0, 0))

                except (
                    ProfileNotExistsException,
                    PrivateProfileNotFollowedException,
                ) as e:
                    # 帳號相關錯誤 - 嚴重錯誤，停止所有下載
                    self.logger.error(
                        f"執行緒中發生帳號相關錯誤 (貼文: {post.shortcode}): {e}"
                    )
                    # 取消所有待處理的任務
                    for f in future_to_post:
                        f.cancel()
                    raise

                except Exception as e:
                    # 其他未預期的錯誤 - 記錄但繼續其他執行緒
                    self.logger.warning(
                        f"執行緒中發生未預期的錯誤 (貼文: {post.shortcode}): "
                        f"{type(e).__name__} - {e}"
                    )
                    # 繼續處理其他貼文
                    results.append((0, 0, 0))

        return results

    def download_stories(self, username: str) -> tuple[int, int]:
        """下載指定使用者的 Stories。

        Stories 是 Instagram 的限時動態功能，發布後 24 小時內有效。
        此方法會下載所有可用的 Stories 並儲存到獨立的 stories/ 子目錄。

        Args:
            username: Instagram 使用者名稱

        Returns:
            tuple[int, int]: (下載的圖片數, 下載的影片數)

        需求：
            - 6.1: WHERE 使用者啟用 Stories 下載選項，THE IG Downloader SHALL 下載目標帳號的所有可用 Stories
            - 6.2: THE IG Downloader SHALL 將 Stories 儲存在獨立的子目錄中
            - 6.3: WHEN Stories 不存在或已過期時，THE IG Downloader SHALL 顯示提示訊息並繼續執行
        """
        images_count = 0
        videos_count = 0

        try:
            self.logger.info(f"開始下載 {username} 的 Stories...")

            # 建立 Stories 專屬目錄
            stories_dir = self.output_dir / username / "stories"
            stories_dir.mkdir(parents=True, exist_ok=True)

            # 獲取使用者的 Profile（使用重試機制）
            profile = self._retry_on_connection_error(
                instaloader.Profile.from_username, self.loader.context, username
            )

            # 獲取 Stories（使用重試機制）
            # get_stories() 需要傳入使用者 ID 列表
            stories_found = False
            stories_iterator = self._retry_on_connection_error(
                self.loader.get_stories, userids=[profile.userid]
            )
            for story in stories_iterator:
                stories_found = True
                self.logger.info(f"找到 Stories，開始下載...")

                # 遍歷 Story 中的每個項目
                for item in story.get_items():
                    try:
                        # 設定下載目標目錄
                        self.loader.dirname_pattern = str(stories_dir)

                        # 下載 Story 項目
                        self.loader.download_storyitem(item, target=username)

                        # 統計下載的檔案類型
                        if item.is_video:
                            videos_count += 1
                            self.logger.info(
                                f"成功下載 Story 影片 (日期: {item.date_local.strftime('%Y-%m-%d %H:%M:%S')})"
                            )
                        else:
                            images_count += 1
                            self.logger.info(
                                f"成功下載 Story 圖片 (日期: {item.date_local.strftime('%Y-%m-%d %H:%M:%S')})"
                            )

                    except Exception as e:
                        # 單個 Story 項目下載失敗，記錄但繼續
                        self.logger.warning(
                            f"下載 Story 項目時發生錯誤: {type(e).__name__} - {e}"
                        )
                        continue

            # 如果沒有找到 Stories
            if not stories_found:
                self.logger.info(
                    f"{username} 目前沒有可用的 Stories（可能已過期或不存在）"
                )

            # 記錄下載摘要
            total_stories = images_count + videos_count
            if total_stories > 0:
                self.logger.info(
                    f"Stories 下載完成 - 共 {total_stories} 個項目 "
                    f"(圖片: {images_count}, 影片: {videos_count})"
                )

            return images_count, videos_count

        except ProfileNotExistsException as e:
            # 帳號不存在 - 重新拋出
            self.logger.error(f"帳號不存在: {username}")
            raise

        except ConnectionException as e:
            # 網路連線錯誤 - 重新拋出
            self.logger.error(f"下載 Stories 時網路連線失敗: {e}")
            raise

        except PrivateProfileNotFollowedException as e:
            # 私人帳號 - 重新拋出
            self.logger.error(f"無法存取私人帳號的 Stories: {username}")
            raise

        except OSError as e:
            if e.errno == errno.ENOSPC:
                # 磁碟空間不足
                self.logger.error("磁碟空間不足，無法下載 Stories")
                raise
            elif e.errno == errno.EACCES:
                # 權限不足
                self.logger.error("檔案權限不足，無法下載 Stories")
                raise
            else:
                # 其他檔案系統錯誤
                self.logger.warning(f"下載 Stories 時發生檔案系統錯誤: {e}")
                return 0, 0

        except Exception as e:
            # 其他未預期的錯誤 - 記錄但不中斷
            self.logger.warning(
                f"下載 Stories 時發生未預期的錯誤: {type(e).__name__} - {e}"
            )
            # 返回 0, 0 表示沒有成功下載任何 Stories
            return 0, 0

    def _is_reel(self, post) -> bool:
        """判斷貼文是否為 Reel 類型。

        Reels 是 Instagram 的短影片功能，具有特定的屬性來識別。
        此方法檢查貼文的 product_type 或其他相關屬性來判斷是否為 Reel。

        Args:
            post: instaloader.Post 物件

        Returns:
            bool: True 如果是 Reel，False 否則

        需求：
            - 8.3: THE IG Downloader SHALL 正確識別貼文是否為 Reel 類型
        """
        try:
            # 檢查 product_type 屬性
            # Reels 的 product_type 通常是 'clips' 或 'igtv'
            if hasattr(post, "product_type"):
                return post.product_type == "clips"

            # 備用檢查：Reels 通常是影片且 typename 為 'GraphVideo'
            # 但這不夠精確，因為一般影片貼文也是 GraphVideo
            # 所以優先使用 product_type
            return False

        except Exception as e:
            # 如果檢查過程中發生錯誤，記錄並返回 False
            self.logger.debug(f"檢查 Reel 類型時發生錯誤: {e}")
            return False

    def _extract_shortcode_from_url(self, url: str) -> str:
        """從 Instagram URL 提取貼文的 shortcode。

        支援的 URL 格式：
        - https://www.instagram.com/p/{shortcode}/
        - https://instagram.com/p/{shortcode}/
        - http://www.instagram.com/p/{shortcode}/
        - https://www.instagram.com/reel/{shortcode}/

        Args:
            url: Instagram 貼文 URL

        Returns:
            str: 貼文的 shortcode

        Raises:
            ValueError: 當 URL 格式不正確時

        需求：
            - 10.2: WHEN 使用者提供貼文 URL 時，THE IG Downloader SHALL 從 URL 中提取貼文的 shortcode
            - 10.5: IF 貼文 URL 格式不正確，THEN THE IG Downloader SHALL 顯示錯誤訊息並終止執行
        """
        # 支援的 URL 格式：
        # https://www.instagram.com/p/ABC123/
        # https://www.instagram.com/reel/ABC123/
        pattern = r"instagram\.com/(?:p|reel)/([A-Za-z0-9_-]+)"
        match = re.search(pattern, url)

        if not match:
            raise ValueError(f"無效的 Instagram URL 格式: {url}")

        shortcode = match.group(1)
        self.logger.debug(f"從 URL 提取 shortcode: {shortcode}")
        return shortcode

    def download_post_from_shortcode(self, shortcode: str) -> DownloadStats:
        """從 shortcode 下載單一貼文。

        Args:
            shortcode: 貼文的 shortcode（唯一識別碼）

        Returns:
            DownloadStats: 下載統計資訊

        Raises:
            ConnectionException: 當網路連線失敗時
            Exception: 當貼文不存在或無法存取時

        需求：
            - 10.3: THE IG Downloader SHALL 使用 shortcode 擷取該貼文的資訊
            - 10.4: THE IG Downloader SHALL 下載該貼文中的所有媒體檔案（圖片或影片）
        """
        start_time = datetime.now()

        try:
            self.logger.info(f"開始下載貼文: {shortcode}")

            # 使用 shortcode 獲取貼文物件（使用重試機制）
            post = self._retry_on_connection_error(
                instaloader.Post.from_shortcode, self.loader.context, shortcode
            )

            # 獲取貼文作者的使用者名稱
            username = post.owner_username
            self.logger.info(f"貼文作者: {username}")
            self.logger.info(
                f"貼文日期: {post.date_local.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            self.logger.info(f"貼文類型: {'影片' if post.is_video else '圖片'}")

            # 建立輸出目錄
            user_dir = self._create_output_directory(username)

            # 下載貼文
            images, videos, skipped = self._download_post(post, username)

            # 記錄結束時間
            end_time = datetime.now()

            # 建立統計資訊
            stats = DownloadStats(
                username=username,
                total_posts=1,
                downloaded_images=images,
                downloaded_videos=videos,
                skipped_files=skipped,
                errors=0,
                output_directory=str(user_dir),
                start_time=start_time,
                end_time=end_time,
            )

            self.logger.info(
                f"貼文下載完成 - 圖片: {images}, 影片: {videos}, 跳過: {skipped}"
            )
            return stats

        except ConnectionException as e:
            # 網路連線錯誤
            self.logger.error(f"下載貼文 {shortcode} 時網路連線失敗: {e}")
            raise

        except Exception as e:
            # 其他錯誤（貼文不存在、私人貼文等）
            self.logger.error(f"下載貼文 {shortcode} 失敗: {type(e).__name__} - {e}")
            raise

    def download_post_from_url(self, url: str) -> DownloadStats:
        """從 URL 下載單一貼文。

        Args:
            url: Instagram 貼文 URL

        Returns:
            DownloadStats: 下載統計資訊

        Raises:
            ValueError: 當 URL 格式不正確時
            ConnectionException: 當網路連線失敗時
            Exception: 當貼文不存在或無法存取時

        需求：
            - 10.1: THE IG Downloader SHALL 接受 Instagram 貼文 URL 作為輸入參數
            - 10.2: WHEN 使用者提供貼文 URL 時，THE IG Downloader SHALL 從 URL 中提取貼文的 shortcode
            - 10.7: THE IG Downloader SHALL 將單一貼文的媒體儲存到指定的輸出目錄中
            - 10.8: WHEN 下載單一貼文時，THE IG Downloader SHALL 顯示貼文的基本資訊（作者、日期等）
        """
        try:
            # 從 URL 提取 shortcode
            shortcode = self._extract_shortcode_from_url(url)

            # 使用 shortcode 下載貼文
            return self.download_post_from_shortcode(shortcode)

        except ValueError as e:
            # URL 格式錯誤
            self.logger.error(f"URL 格式錯誤: {e}")
            raise

        except Exception as e:
            # 其他錯誤
            self.logger.error(f"從 URL 下載貼文失敗: {e}")
            raise

    def _read_urls_from_file(self, file_path: str) -> list[str]:
        """從 YAML 檔案讀取 URL 列表。

        支援兩種 YAML 格式：
        1. 簡化格式：直接是 URL 字串列表
        2. 詳細格式：包含 url 和 description 的字典列表

        Args:
            file_path: YAML 檔案路徑

        Returns:
            list[str]: URL 列表

        Raises:
            FileNotFoundError: 當檔案不存在時
            ValueError: 當 YAML 格式錯誤時

        需求：
            - 10.1: THE IG Downloader SHALL 接受 Instagram 貼文 URL 作為輸入參數
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not data or "urls" not in data:
                raise ValueError("YAML 檔案格式錯誤：缺少 'urls' 欄位")

            url_list = data["urls"]
            urls = []

            for item in url_list:
                # 支援兩種格式：
                # 1. 字串格式：直接是 URL
                # 2. 字典格式：包含 url 和 description
                if isinstance(item, str):
                    url = item
                elif isinstance(item, dict) and "url" in item:
                    url = item["url"]
                else:
                    self.logger.warning(f"跳過無效的項目: {item}")
                    continue

                # 驗證 URL 格式
                if "instagram.com" in url:
                    urls.append(url)
                else:
                    self.logger.warning(f"跳過無效的 URL: {url}")

            self.logger.info(f"從 {file_path} 讀取了 {len(urls)} 個 URL")
            return urls

        except yaml.YAMLError as e:
            raise ValueError(f"YAML 檔案解析錯誤: {e}")
        except FileNotFoundError:
            raise FileNotFoundError(f"找不到檔案: {file_path}")

    def _save_failed_urls(self, failed_urls: list[dict]) -> None:
        """儲存失敗的 URL 到 YAML 檔案。

        Args:
            failed_urls: 失敗的 URL 列表，每個元素包含 url、error、timestamp

        需求：
            - 10.1: THE IG Downloader SHALL 接受 Instagram 貼文 URL 作為輸入參數
        """
        failed_file = self.output_dir / "failed_downloads.yaml"

        data = {"failed_downloads": failed_urls}

        try:
            with open(failed_file, "w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

            self.logger.info(f"失敗的 URL 已記錄到: {failed_file}")
        except Exception as e:
            self.logger.error(f"無法儲存失敗記錄: {e}")

    def download_posts_from_urls(
        self, urls: list[str], max_retries: int = 3
    ) -> DownloadStats:
        """從多個 URL 批次下載貼文，支援失敗重試。

        Args:
            urls: Instagram 貼文 URL 列表
            max_retries: 最大重試次數，預設為 3

        Returns:
            DownloadStats: 下載統計資訊

        需求：
            - 10.1: THE IG Downloader SHALL 接受 Instagram 貼文 URL 作為輸入參數
            - 10.4: THE IG Downloader SHALL 下載該貼文中的所有媒體檔案（圖片或影片）
        """
        start_time = datetime.now()

        total_posts = len(urls)
        downloaded_images = 0
        downloaded_videos = 0
        skipped_files = 0
        errors = 0
        failed_urls = []

        self.logger.info(f"開始批次下載 {total_posts} 個貼文")

        # 使用單執行緒或多執行緒下載
        if self.max_workers == 1:
            # 單執行緒模式 - 使用進度條
            with tqdm(
                total=total_posts, desc="下載貼文", unit="post", ncols=100
            ) as pbar:
                for url in urls:
                    success = False
                    last_error = None

                    # 重試機制
                    for attempt in range(max_retries):
                        try:
                            stats = self.download_post_from_url(url)
                            downloaded_images += stats.downloaded_images
                            downloaded_videos += stats.downloaded_videos
                            skipped_files += stats.skipped_files
                            success = True
                            break
                        except Exception as e:
                            last_error = e
                            if attempt < max_retries - 1:
                                wait_time = (attempt + 1) * 2  # 2秒、4秒、6秒
                                self.logger.warning(
                                    f"下載失敗 (嘗試 {attempt + 1}/{max_retries}): {url} - {e}，"
                                    f"{wait_time} 秒後重試"
                                )
                                time.sleep(wait_time)

                    # 記錄失敗的 URL
                    if not success:
                        failed_urls.append(
                            {
                                "url": url,
                                "error": str(last_error),
                                "timestamp": datetime.now().isoformat(),
                            }
                        )
                        self.logger.error(
                            f"下載失敗（已重試 {max_retries} 次）: {url} - {last_error}"
                        )
                        errors += 1

                    # 更新進度條
                    pbar.update(1)
                    pbar.set_postfix(
                        {
                            "成功": total_posts
                            - errors
                            - (pbar.n - (total_posts - errors)),
                            "失敗": errors,
                        }
                    )
        else:
            # 多執行緒模式 - 使用進度條
            self.logger.info(f"使用 {self.max_workers} 個執行緒並行下載")

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 為每個 URL 建立重試包裝函數
                def download_with_retry(url):
                    for attempt in range(max_retries):
                        try:
                            return self.download_post_from_url(url), None
                        except Exception as e:
                            if attempt < max_retries - 1:
                                wait_time = (attempt + 1) * 2
                                self.logger.warning(
                                    f"下載失敗 (嘗試 {attempt + 1}/{max_retries}): {url} - {e}，"
                                    f"{wait_time} 秒後重試"
                                )
                                time.sleep(wait_time)
                            else:
                                return None, e
                    return None, Exception("Unknown error")

                # 提交所有任務
                future_to_url = {
                    executor.submit(download_with_retry, url): url for url in urls
                }

                # 使用進度條追蹤完成進度
                with tqdm(
                    total=total_posts,
                    desc="並行下載",
                    unit="post",
                    ncols=100,
                    bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
                ) as pbar:
                    # 處理完成的任務
                    for future in as_completed(future_to_url):
                        url = future_to_url[future]
                        try:
                            stats, error = future.result()

                            if stats:
                                with self.stats_lock:
                                    downloaded_images += stats.downloaded_images
                                    downloaded_videos += stats.downloaded_videos
                                    skipped_files += stats.skipped_files
                            else:
                                # 下載失敗
                                with self.stats_lock:
                                    failed_urls.append(
                                        {
                                            "url": url,
                                            "error": str(error),
                                            "timestamp": datetime.now().isoformat(),
                                        }
                                    )
                                    errors += 1
                                    self.logger.error(
                                        f"下載失敗（已重試 {max_retries} 次）: {url} - {error}"
                                    )
                        except Exception as e:
                            with self.stats_lock:
                                failed_urls.append(
                                    {
                                        "url": url,
                                        "error": str(e),
                                        "timestamp": datetime.now().isoformat(),
                                    }
                                )
                                errors += 1
                                self.logger.error(f"處理任務時發生錯誤: {url} - {e}")

                        # 更新進度條
                        pbar.update(1)
                        with self.stats_lock:
                            success_count = pbar.n - errors
                            pbar.set_postfix({"成功": success_count, "失敗": errors})

        # 儲存失敗的 URL
        if failed_urls:
            self._save_failed_urls(failed_urls)

        # 記錄結束時間
        end_time = datetime.now()

        # 建立統計資訊
        stats = DownloadStats(
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

        self.logger.info(f"批次下載完成 - 成功: {total_posts - errors}, 失敗: {errors}")
        return stats

    def download_reels(self, username: str) -> tuple[int, int]:
        """下載指定使用者的 Reels 短影片。

        Reels 是 Instagram 的短影片功能，此方法會遍歷使用者的貼文，
        識別並下載所有 Reels 影片到獨立的 reels/ 子目錄。

        Args:
            username: Instagram 使用者名稱

        Returns:
            tuple[int, int]: (下載的圖片數, 下載的影片數)
            注意：Reels 只有影片，所以圖片數永遠是 0

        需求：
            - 8.1: WHERE 使用者啟用 Reels 下載選項，THE IG Downloader SHALL 下載目標帳號的所有 Reels 影片
            - 8.2: THE IG Downloader SHALL 將 Reels 儲存在獨立的子目錄中
            - 8.3: THE IG Downloader SHALL 正確識別貼文是否為 Reel 類型
            - 8.5: WHEN Reels 不存在時，THE IG Downloader SHALL 顯示提示訊息並繼續執行
        """
        images_count = 0  # Reels 只有影片，圖片數永遠是 0
        videos_count = 0

        try:
            self.logger.info(f"開始下載 {username} 的 Reels...")

            # 建立 Reels 專屬目錄
            reels_dir = self.output_dir / username / "reels"
            reels_dir.mkdir(parents=True, exist_ok=True)

            # 獲取使用者的 Profile（使用重試機制）
            profile = self._retry_on_connection_error(
                instaloader.Profile.from_username, self.loader.context, username
            )

            # 遍歷使用者的所有貼文，尋找 Reels
            reels_found = False
            for post in profile.get_posts():
                try:
                    # 檢查是否為 Reel
                    if not self._is_reel(post):
                        continue

                    reels_found = True

                    # 檢查是否已下載（斷點續傳）
                    if self.resume and self._is_already_downloaded(post.shortcode):
                        self.logger.info(
                            f"跳過已下載的 Reel: {post.shortcode} "
                            f"(日期: {post.date_local.strftime('%Y-%m-%d')})"
                        )
                        continue

                    # 檢查檔案是否已存在
                    existing_files = list(reels_dir.glob(f"*{post.shortcode}*"))
                    if existing_files:
                        self.logger.info(
                            f"Reel 檔案已存在，跳過: {post.shortcode} "
                            f"(找到 {len(existing_files)} 個檔案)"
                        )
                        continue

                    # 記錄下載開始
                    self.logger.info(
                        f"開始下載 Reel: {post.shortcode} "
                        f"(日期: {post.date_local.strftime('%Y-%m-%d')})"
                    )

                    # 設定下載目標目錄
                    self.loader.dirname_pattern = str(reels_dir)

                    # 下載 Reel
                    self.loader.download_post(post, target=username)

                    videos_count += 1
                    self.logger.info(f"成功下載 Reel: {post.shortcode}")

                    # 更新已下載集合（用於斷點續傳）
                    if self.resume:
                        with self.stats_lock:
                            self.downloaded_posts.add(post.shortcode)
                            # 立即儲存進度
                            self._save_progress(username, self.downloaded_posts)

                except ConnectionException as e:
                    # 網路連線錯誤 - 記錄並重新拋出
                    self.logger.error(f"下載 Reel {post.shortcode} 時網路連線失敗: {e}")
                    raise

                except OSError as e:
                    if e.errno == errno.ENOSPC:
                        # 磁碟空間不足 - 嚴重錯誤
                        self.logger.error(
                            f"磁碟空間不足，無法下載 Reel {post.shortcode}"
                        )
                        raise
                    elif e.errno == errno.EACCES:
                        # 權限不足 - 嚴重錯誤
                        self.logger.error(
                            f"檔案權限不足，無法下載 Reel {post.shortcode}"
                        )
                        raise
                    else:
                        # 其他檔案系統錯誤 - 記錄但繼續
                        self.logger.warning(
                            f"下載 Reel {post.shortcode} 時發生檔案系統錯誤: {e}"
                        )
                        continue

                except Exception as e:
                    # 單個 Reel 下載失敗，記錄但繼續
                    self.logger.warning(
                        f"下載 Reel {post.shortcode} 時發生錯誤: {type(e).__name__} - {e}"
                    )
                    continue

            # 如果沒有找到 Reels
            if not reels_found:
                self.logger.info(f"{username} 目前沒有可用的 Reels")

            # 記錄下載摘要
            if videos_count > 0:
                self.logger.info(f"Reels 下載完成 - 共 {videos_count} 個影片")

            return images_count, videos_count

        except ProfileNotExistsException as e:
            # 帳號不存在 - 重新拋出
            self.logger.error(f"帳號不存在: {username}")
            raise

        except ConnectionException as e:
            # 網路連線錯誤 - 重新拋出
            self.logger.error(f"下載 Reels 時網路連線失敗: {e}")
            raise

        except PrivateProfileNotFollowedException as e:
            # 私人帳號 - 重新拋出
            self.logger.error(f"無法存取私人帳號的 Reels: {username}")
            raise

        except OSError as e:
            if e.errno == errno.ENOSPC:
                # 磁碟空間不足
                self.logger.error("磁碟空間不足，無法下載 Reels")
                raise
            elif e.errno == errno.EACCES:
                # 權限不足
                self.logger.error("檔案權限不足，無法下載 Reels")
                raise
            else:
                # 其他檔案系統錯誤
                self.logger.warning(f"下載 Reels 時發生檔案系統錯誤: {e}")
                return 0, 0

        except Exception as e:
            # 其他未預期的錯誤 - 記錄但不中斷
            self.logger.warning(
                f"下載 Reels 時發生未預期的錯誤: {type(e).__name__} - {e}"
            )
            # 返回 0, 0 表示沒有成功下載任何 Reels
            return 0, 0

    def download_user_media(
        self,
        username: str,
        max_posts: int | None = None,
        include_stories: bool = False,
        include_reels: bool = False,
    ) -> DownloadStats:
        """下載指定使用者的媒體檔案。

        此方法整合所有下載功能，按照以下順序執行：
        1. Stories（如果啟用）
        2. Reels（如果啟用）
        3. 一般貼文

        Args:
            username: Instagram 使用者名稱
            max_posts: 限制下載的貼文數量，None 表示下載所有貼文
            include_stories: 是否下載 Stories，預設為 False
            include_reels: 是否下載 Reels，預設為 False

        Returns:
            DownloadStats: 下載統計資訊

        Raises:
            ProfileNotExistsException: 當帳號不存在時
            ConnectionException: 當網路連線失敗時
            PrivateProfileNotFollowedException: 當帳號為私人帳號時
            OSError: 當磁碟空間不足或權限不足時

        需求：
            - 1.2: WHEN 使用者提供有效的帳號名稱時，THE IG Downloader SHALL 連接到 Instagram 並擷取該帳號的貼文資訊
            - 3.1: WHEN 開始下載時，THE IG Downloader SHALL 顯示目標帳號的基本資訊
            - 3.2: WHILE 下載進行中，THE IG Downloader SHALL 顯示當前正在處理的貼文資訊
            - 6.5: THE IG Downloader SHALL 優先下載 Stories 再下載一般貼文
        """
        # 記錄開始時間
        start_time = datetime.now()

        # 初始化統計資料
        total_posts = 0
        downloaded_images = 0
        downloaded_videos = 0
        skipped_files = 0
        errors = 0
        stories_images = 0
        stories_videos = 0
        reels_videos = 0

        try:
            # 建立輸出目錄
            user_dir = self._create_output_directory(username)

            # 載入下載進度（如果啟用斷點續傳）
            if self.resume:
                self.downloaded_posts = self._load_progress(username)
                resumed_from_previous = len(self.downloaded_posts) > 0
                if resumed_from_previous:
                    self.logger.info(
                        f"啟用斷點續傳 - 已下載 {len(self.downloaded_posts)} 個項目"
                    )
            else:
                resumed_from_previous = False

            # 獲取使用者的 Profile（使用重試機制）
            self.logger.info(f"正在連接到 Instagram 並獲取 {username} 的資訊...")
            profile = self._retry_on_connection_error(
                instaloader.Profile.from_username, self.loader.context, username
            )

            # 顯示帳號基本資訊
            self.logger.info(f"帳號資訊 - 使用者名稱: {username}")
            self.logger.info(f"帳號資訊 - 全名: {profile.full_name}")
            self.logger.info(f"帳號資訊 - 貼文數量: {profile.mediacount}")
            self.logger.info(f"帳號資訊 - 追蹤者: {profile.followers}")

            # 步驟 1: 下載 Stories（如果啟用）
            if include_stories:
                self.logger.info("=" * 60)
                self.logger.info("步驟 1/3: 下載 Stories")
                self.logger.info("=" * 60)
                try:
                    stories_images, stories_videos = self.download_stories(username)
                    self.logger.info(
                        f"Stories 下載完成 - 圖片: {stories_images}, 影片: {stories_videos}"
                    )
                except Exception as e:
                    # Stories 下載失敗不影響後續下載
                    self.logger.warning(f"Stories 下載失敗: {type(e).__name__} - {e}")
                    errors += 1

            # 步驟 2: 下載 Reels（如果啟用）
            if include_reels:
                self.logger.info("=" * 60)
                self.logger.info(
                    f"步驟 {'2/3' if include_stories else '1/2'}: 下載 Reels"
                )
                self.logger.info("=" * 60)
                try:
                    _, reels_videos = self.download_reels(username)
                    self.logger.info(f"Reels 下載完成 - 影片: {reels_videos}")
                except Exception as e:
                    # Reels 下載失敗不影響後續下載
                    self.logger.warning(f"Reels 下載失敗: {type(e).__name__} - {e}")
                    errors += 1

            # 步驟 3: 下載一般貼文
            step_num = 1
            if include_stories:
                step_num += 1
            if include_reels:
                step_num += 1
            total_steps = step_num

            self.logger.info("=" * 60)
            self.logger.info(f"步驟 {step_num}/{total_steps}: 下載一般貼文")
            self.logger.info("=" * 60)

            # 收集要下載的貼文
            posts_to_download = []
            self.logger.info("正在收集貼文列表...")

            for post in profile.get_posts():
                # 如果設定了最大貼文數量限制
                if max_posts is not None and len(posts_to_download) >= max_posts:
                    self.logger.info(f"已達到最大貼文數量限制: {max_posts}")
                    break

                # 跳過 Reels（如果已經在步驟 2 下載過）
                if include_reels and self._is_reel(post):
                    continue

                posts_to_download.append(post)

            total_posts = len(posts_to_download)
            self.logger.info(f"找到 {total_posts} 個一般貼文")

            # 下載貼文（使用單執行緒或多執行緒）
            if total_posts > 0:
                if self.max_workers == 1:
                    self.logger.info("使用單執行緒模式下載貼文")
                else:
                    self.logger.info(f"使用 {self.max_workers} 個執行緒並行下載貼文")

                # 使用並行下載方法（內部會根據 max_workers 決定是否真的並行）
                results = self._download_posts_parallel(posts_to_download, username)

                # 統計結果
                for images, videos, skipped in results:
                    downloaded_images += images
                    downloaded_videos += videos
                    skipped_files += skipped

                self.logger.info(
                    f"一般貼文下載完成 - 圖片: {downloaded_images}, "
                    f"影片: {downloaded_videos}, 跳過: {skipped_files}"
                )
            else:
                self.logger.info("沒有需要下載的一般貼文")

            # 記錄結束時間
            end_time = datetime.now()

            # 建立統計資訊
            stats = DownloadStats(
                username=username,
                total_posts=total_posts,
                downloaded_images=downloaded_images,
                downloaded_videos=downloaded_videos,
                skipped_files=skipped_files,
                errors=errors,
                output_directory=str(user_dir),
                start_time=start_time,
                end_time=end_time,
                stories_downloaded=stories_images + stories_videos,
                reels_downloaded=reels_videos,
                resumed_from_previous=resumed_from_previous,
            )

            # 記錄完成訊息
            self.logger.info("=" * 60)
            self.logger.info("下載完成！")
            self.logger.info("=" * 60)
            self.logger.info(f"總耗時: {stats.duration}")
            self.logger.info(f"總下載檔案數: {stats.total_files}")
            self.logger.info(f"輸出目錄: {stats.output_directory}")

            return stats

        except ProfileNotExistsException as e:
            # 帳號不存在 - 嚴重錯誤
            self.logger.error(f"帳號不存在: {username}")
            raise

        except ConnectionException as e:
            # 網路連線錯誤 - 嚴重錯誤
            self.logger.error(f"網路連線失敗: {e}")
            raise

        except PrivateProfileNotFollowedException as e:
            # 私人帳號 - 嚴重錯誤
            self.logger.error(f"無法存取私人帳號: {username}")
            raise

        except OSError as e:
            if e.errno == errno.ENOSPC:
                # 磁碟空間不足
                self.logger.error("磁碟空間不足")
                raise
            elif e.errno == errno.EACCES:
                # 權限不足
                self.logger.error("檔案權限不足")
                raise
            else:
                # 其他檔案系統錯誤
                self.logger.error(f"檔案系統錯誤: {e}")
                raise

        except Exception as e:
            # 其他未預期的錯誤
            self.logger.error(f"下載過程中發生未預期的錯誤: {type(e).__name__} - {e}")
            raise
