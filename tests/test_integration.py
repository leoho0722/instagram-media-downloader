"""整合測試 - 測試完整下載流程。"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from ig_media_downloader.downloader import IGDownloader


class TestDownloadUserMedia:
    """測試完整下載流程。"""

    @patch("ig_media_downloader.downloader.instaloader.Profile")
    @patch("ig_media_downloader.downloader.instaloader.Instaloader")
    def test_download_user_media_basic(
        self, mock_loader_class, mock_profile_class, temp_dir
    ):
        """測試基本下載流程。

        需求：1.2 - WHEN 使用者提供有效的帳號名稱時，THE IG Downloader SHALL 連接到 Instagram 並擷取該帳號的貼文資訊
        """
        # 設定 mock profile
        mock_profile = Mock()
        mock_profile.username = "test_user"
        mock_profile.full_name = "Test User"
        mock_profile.mediacount = 2
        mock_profile.followers = 100

        # 建立 mock posts
        mock_post1 = Mock()
        mock_post1.shortcode = "POST001"
        mock_post1.is_video = False
        mock_post1.typename = "GraphImage"
        mock_post1.date_local = datetime(2024, 1, 15, 10, 0, 0)

        mock_post2 = Mock()
        mock_post2.shortcode = "POST002"
        mock_post2.is_video = True
        mock_post2.typename = "GraphVideo"
        mock_post2.date_local = datetime(2024, 1, 14, 10, 0, 0)

        mock_profile.get_posts.return_value = [mock_post1, mock_post2]
        mock_profile_class.from_username.return_value = mock_profile

        # 建立下載器
        downloader = IGDownloader(output_dir=str(temp_dir), resume=False)

        # Mock download_post 方法
        with patch.object(downloader.loader, "download_post"):
            stats = downloader.download_user_media("test_user")

        # 驗證結果
        assert stats.username == "test_user"
        assert stats.total_posts == 2
        assert stats.output_directory == str(temp_dir / "test_user")

    @patch("ig_media_downloader.downloader.instaloader.Profile")
    @patch("ig_media_downloader.downloader.instaloader.Instaloader")
    def test_download_with_resume(
        self, mock_loader_class, mock_profile_class, temp_dir, create_progress_file
    ):
        """測試斷點續傳功能。

        需求：9.1 - THE IG Downloader SHALL 預設啟用斷點續傳功能
        """
        # 建立進度檔案
        create_progress_file()

        # 設定 mock profile
        mock_profile = Mock()
        mock_profile.username = "test_user"
        mock_profile.full_name = "Test User"
        mock_profile.mediacount = 3
        mock_profile.followers = 100

        # 建立 mock posts（包含已下載和未下載的）
        mock_post1 = Mock()
        mock_post1.shortcode = "ABC123"  # 已下載
        mock_post1.is_video = False
        mock_post1.typename = "GraphImage"
        mock_post1.date_local = datetime(2024, 1, 15, 10, 0, 0)

        mock_post2 = Mock()
        mock_post2.shortcode = "NEW001"  # 未下載
        mock_post2.is_video = True
        mock_post2.typename = "GraphVideo"
        mock_post2.date_local = datetime(2024, 1, 14, 10, 0, 0)

        mock_profile.get_posts.return_value = [mock_post1, mock_post2]
        mock_profile_class.from_username.return_value = mock_profile

        # 建立下載器（啟用斷點續傳）
        downloader = IGDownloader(output_dir=str(temp_dir), resume=True)

        # Mock download_post 方法
        with patch.object(downloader.loader, "download_post"):
            stats = downloader.download_user_media("test_user")

        # 驗證結果
        assert stats.resumed_from_previous is True
        assert stats.skipped_files > 0  # 應該有跳過的檔案


class TestMultiThreadedDownload:
    """測試多執行緒下載功能。"""

    def test_download_posts_parallel_single_thread(self, temp_dir):
        """測試單執行緒模式。

        需求：7.2 - THE IG Downloader SHALL 預設使用單執行緒模式以避免對伺服器造成過大負擔
        """
        downloader = IGDownloader(output_dir=str(temp_dir), max_workers=1)

        # 建立 mock posts
        mock_posts = []
        for i in range(3):
            mock_post = Mock()
            mock_post.shortcode = f"POST{i:03d}"
            mock_post.is_video = False
            mock_post.typename = "GraphImage"
            mock_post.date_local = datetime(2024, 1, 15, 10, 0, 0)
            mock_posts.append(mock_post)

        # Mock _download_post 方法
        with patch.object(downloader, "_download_post", return_value=(1, 0, 0)):
            results = downloader._download_posts_parallel(mock_posts, "test_user")

        # 驗證結果
        assert len(results) == 3
        assert all(r == (1, 0, 0) for r in results)

    def test_download_posts_parallel_multi_thread(self, temp_dir):
        """測試多執行緒模式。

        需求：7.1 - WHERE 使用者指定執行緒數量，THE IG Downloader SHALL 使用指定數量的執行緒進行並行下載
        """
        downloader = IGDownloader(output_dir=str(temp_dir), max_workers=4)

        # 建立 mock posts
        mock_posts = []
        for i in range(5):
            mock_post = Mock()
            mock_post.shortcode = f"POST{i:03d}"
            mock_post.is_video = False
            mock_post.typename = "GraphImage"
            mock_post.date_local = datetime(2024, 1, 15, 10, 0, 0)
            mock_posts.append(mock_post)

        # Mock _download_post 方法
        with patch.object(downloader, "_download_post", return_value=(1, 0, 0)):
            results = downloader._download_posts_parallel(mock_posts, "test_user")

        # 驗證結果
        assert len(results) == 5
        assert all(r == (1, 0, 0) for r in results)


class TestStoriesDownload:
    """測試 Stories 下載功能。"""

    @patch("ig_media_downloader.downloader.instaloader.Profile")
    def test_download_stories_success(self, mock_profile_class, temp_dir):
        """測試成功下載 Stories。

        需求：6.1 - WHERE 使用者啟用 Stories 下載選項，THE IG Downloader SHALL 下載目標帳號的所有可用 Stories
        """
        downloader = IGDownloader(output_dir=str(temp_dir))

        # 設定 mock profile
        mock_profile = Mock()
        mock_profile.userid = 12345
        mock_profile_class.from_username.return_value = mock_profile

        # 建立 mock story items
        mock_story_item1 = Mock()
        mock_story_item1.is_video = False
        mock_story_item1.date_local = datetime(2024, 1, 16, 10, 0, 0)

        mock_story_item2 = Mock()
        mock_story_item2.is_video = True
        mock_story_item2.date_local = datetime(2024, 1, 16, 11, 0, 0)

        mock_story = Mock()
        mock_story.get_items.return_value = [mock_story_item1, mock_story_item2]

        # Mock get_stories
        with patch.object(downloader.loader, "get_stories", return_value=[mock_story]):
            with patch.object(downloader.loader, "download_storyitem"):
                images, videos = downloader.download_stories("test_user")

        # 驗證結果
        assert images == 1
        assert videos == 1

    @patch("ig_media_downloader.downloader.instaloader.Profile")
    def test_download_stories_no_stories(self, mock_profile_class, temp_dir):
        """測試沒有 Stories 的情況。

        需求：6.3 - WHEN Stories 不存在或已過期時，THE IG Downloader SHALL 顯示提示訊息並繼續執行
        """
        downloader = IGDownloader(output_dir=str(temp_dir))

        # 設定 mock profile
        mock_profile = Mock()
        mock_profile.userid = 12345
        mock_profile_class.from_username.return_value = mock_profile

        # Mock get_stories 返回空列表
        with patch.object(downloader.loader, "get_stories", return_value=[]):
            images, videos = downloader.download_stories("test_user")

        # 驗證結果
        assert images == 0
        assert videos == 0


class TestReelsDownload:
    """測試 Reels 下載功能。"""

    @patch("ig_media_downloader.downloader.instaloader.Profile")
    def test_download_reels_success(self, mock_profile_class, temp_dir):
        """測試成功下載 Reels。

        需求：8.1 - WHERE 使用者啟用 Reels 下載選項，THE IG Downloader SHALL 下載目標帳號的所有 Reels 影片
        """
        downloader = IGDownloader(output_dir=str(temp_dir), resume=False)

        # 設定 mock profile
        mock_profile = Mock()
        mock_profile.username = "test_user"

        # 建立 mock posts（包含 Reels 和一般貼文）
        mock_reel1 = Mock()
        mock_reel1.shortcode = "REEL001"
        mock_reel1.is_video = True
        mock_reel1.product_type = "clips"
        mock_reel1.date_local = datetime(2024, 1, 15, 10, 0, 0)

        mock_post = Mock()
        mock_post.shortcode = "POST001"
        mock_post.is_video = False
        mock_post.product_type = "feed"
        mock_post.date_local = datetime(2024, 1, 14, 10, 0, 0)

        mock_reel2 = Mock()
        mock_reel2.shortcode = "REEL002"
        mock_reel2.is_video = True
        mock_reel2.product_type = "clips"
        mock_reel2.date_local = datetime(2024, 1, 13, 10, 0, 0)

        mock_profile.get_posts.return_value = [mock_reel1, mock_post, mock_reel2]
        mock_profile_class.from_username.return_value = mock_profile

        # Mock download_post
        with patch.object(downloader.loader, "download_post"):
            images, videos = downloader.download_reels("test_user")

        # 驗證結果
        assert images == 0  # Reels 只有影片
        assert videos == 2

    @patch("ig_media_downloader.downloader.instaloader.Profile")
    def test_download_reels_no_reels(self, mock_profile_class, temp_dir):
        """測試沒有 Reels 的情況。

        需求：8.5 - WHEN Reels 不存在時，THE IG Downloader SHALL 顯示提示訊息並繼續執行
        """
        downloader = IGDownloader(output_dir=str(temp_dir))

        # 設定 mock profile
        mock_profile = Mock()
        mock_profile.username = "test_user"

        # 建立 mock posts（只有一般貼文，沒有 Reels）
        mock_post = Mock()
        mock_post.shortcode = "POST001"
        mock_post.is_video = False
        mock_post.product_type = "feed"
        mock_post.date_local = datetime(2024, 1, 14, 10, 0, 0)

        mock_profile.get_posts.return_value = [mock_post]
        mock_profile_class.from_username.return_value = mock_profile

        images, videos = downloader.download_reels("test_user")

        # 驗證結果
        assert images == 0
        assert videos == 0
