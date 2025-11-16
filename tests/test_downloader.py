"""測試下載器核心功能 - IGDownloader。"""

import errno
import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from instaloader.exceptions import (
    ConnectionException,
    ProfileNotExistsException,
    PrivateProfileNotFollowedException,
)

from ig_media_downloader.downloader import IGDownloader


class TestIGDownloaderInit:
    """測試 IGDownloader 初始化。"""

    def test_init_default_values(self, temp_dir):
        """測試預設參數初始化。"""
        downloader = IGDownloader(output_dir=str(temp_dir))

        assert downloader.output_dir == temp_dir
        assert downloader.max_workers == 1
        assert downloader.resume is True
        assert isinstance(downloader.downloaded_posts, set)
        assert len(downloader.downloaded_posts) == 0

    def test_init_custom_workers(self, temp_dir):
        """測試自訂執行緒數量。

        需求：7.1 - WHERE 使用者指定執行緒數量，THE IG Downloader SHALL 使用指定數量的執行緒進行並行下載
        """
        downloader = IGDownloader(output_dir=str(temp_dir), max_workers=4)
        assert downloader.max_workers == 4

    def test_init_max_workers_limit(self, temp_dir):
        """測試執行緒數量上限。

        需求：7.3 - THE IG Downloader SHALL 限制最大執行緒數量不超過 8 個
        """
        downloader = IGDownloader(output_dir=str(temp_dir), max_workers=20)
        assert downloader.max_workers == 8


class TestProgressManagement:
    """測試進度管理功能（斷點續傳）。"""

    def test_load_progress_file_not_exists(self, temp_dir):
        """測試載入不存在的進度檔案。

        需求：9.3 - WHEN 開始下載時，THE IG Downloader SHALL 載入先前的下載進度
        """
        downloader = IGDownloader(output_dir=str(temp_dir))
        result = downloader._load_progress("test_user")

        assert isinstance(result, set)
        assert len(result) == 0

    def test_load_progress_success(self, temp_dir, create_progress_file):
        """測試成功載入進度檔案。

        需求：9.3 - WHEN 開始下載時，THE IG Downloader SHALL 載入先前的下載進度
        """
        create_progress_file()
        downloader = IGDownloader(output_dir=str(temp_dir))
        result = downloader._load_progress("test_user")

        assert isinstance(result, set)
        assert "ABC123" in result
        assert "XYZ789" in result
        assert "REEL001" in result
        assert len(result) == 3

    def test_load_progress_corrupted_file(self, temp_dir):
        """測試載入損壞的進度檔案。

        需求：9.6 - IF 進度記錄檔案損壞或無法讀取，THEN THE IG Downloader SHALL 從頭開始下載
        """
        # 建立損壞的 JSON 檔案
        user_dir = temp_dir / "test_user"
        user_dir.mkdir(parents=True, exist_ok=True)
        progress_file = user_dir / ".download_progress.json"

        with open(progress_file, "w") as f:
            f.write("{ invalid json }")

        downloader = IGDownloader(output_dir=str(temp_dir))
        result = downloader._load_progress("test_user")

        # 應該返回空集合
        assert isinstance(result, set)
        assert len(result) == 0

    def test_save_progress(self, temp_dir):
        """測試儲存進度檔案。

        需求：9.5 - THE IG Downloader SHALL 在每個貼文下載完成後立即更新進度記錄
        """
        downloader = IGDownloader(output_dir=str(temp_dir))
        downloaded_posts = {"ABC123", "XYZ789"}

        downloader._save_progress("test_user", downloaded_posts)

        # 驗證檔案是否建立
        progress_file = temp_dir / "test_user" / ".download_progress.json"
        assert progress_file.exists()

        # 驗證檔案內容
        with open(progress_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["username"] == "test_user"
        assert set(data["downloaded_posts"]) == downloaded_posts
        assert "last_updated" in data

    def test_is_already_downloaded(self, temp_dir):
        """測試檢查貼文是否已下載。

        需求：9.4 - THE IG Downloader SHALL 跳過已下載的貼文和媒體檔案
        """
        downloader = IGDownloader(output_dir=str(temp_dir))
        downloader.downloaded_posts = {"ABC123", "XYZ789"}

        assert downloader._is_already_downloaded("ABC123") is True
        assert downloader._is_already_downloaded("XYZ789") is True
        assert downloader._is_already_downloaded("NEW123") is False


class TestErrorHandling:
    """測試錯誤處理機制。"""

    def test_handle_profile_not_exists(self, temp_dir):
        """測試處理帳號不存在錯誤。

        需求：1.3 - IF 提供的帳號名稱不存在，THEN THE IG Downloader SHALL 顯示錯誤訊息並終止執行
        """
        downloader = IGDownloader(output_dir=str(temp_dir))
        error = ProfileNotExistsException("test_user")

        with pytest.raises(ProfileNotExistsException):
            downloader._handle_download_error(error, "test context")

    def test_handle_connection_error(self, temp_dir):
        """測試處理網路連線錯誤。

        需求：4.1 - IF 網路連線失敗，THEN THE IG Downloader SHALL 顯示網路錯誤訊息並提供重試選項
        """
        downloader = IGDownloader(output_dir=str(temp_dir))
        error = ConnectionException("Network error")

        with pytest.raises(ConnectionException):
            downloader._handle_download_error(error, "test context")

    def test_handle_private_profile(self, temp_dir):
        """測試處理私人帳號錯誤。

        需求：4.2 - IF Instagram API 回應錯誤，THEN THE IG Downloader SHALL 記錄錯誤詳情並繼續處理其他貼文
        """
        downloader = IGDownloader(output_dir=str(temp_dir))
        error = PrivateProfileNotFollowedException("test_user")

        with pytest.raises(PrivateProfileNotFollowedException):
            downloader._handle_download_error(error, "test context")

    def test_handle_disk_space_error(self, temp_dir):
        """測試處理磁碟空間不足錯誤。

        需求：4.3 - IF 磁碟空間不足，THEN THE IG Downloader SHALL 顯示警告訊息並停止下載
        """
        downloader = IGDownloader(output_dir=str(temp_dir))
        error = OSError(errno.ENOSPC, "No space left on device")

        with pytest.raises(OSError):
            downloader._handle_download_error(error, "test context")

    def test_handle_permission_error(self, temp_dir):
        """測試處理權限不足錯誤。

        需求：4.4 - IF 檔案寫入權限不足，THEN THE IG Downloader SHALL 顯示權限錯誤訊息並終止執行
        """
        downloader = IGDownloader(output_dir=str(temp_dir))
        error = OSError(errno.EACCES, "Permission denied")

        with pytest.raises(OSError):
            downloader._handle_download_error(error, "test context")

    def test_handle_generic_error(self, temp_dir):
        """測試處理一般錯誤（不中斷執行）。

        需求：4.2 - IF Instagram API 回應錯誤，THEN THE IG Downloader SHALL 記錄錯誤詳情並繼續處理其他貼文
        """
        downloader = IGDownloader(output_dir=str(temp_dir))
        error = ValueError("Some generic error")

        # 一般錯誤不應該拋出異常
        downloader._handle_download_error(error, "test context")


class TestDirectoryCreation:
    """測試目錄建立功能。"""

    def test_create_output_directory(self, temp_dir):
        """測試建立輸出目錄。

        需求：2.1 - THE IG Downloader SHALL 建立一個以目標帳號名稱命名的下載目錄
        需求：2.2 - WHEN 下載目錄不存在時，THE IG Downloader SHALL 自動建立該目錄
        """
        downloader = IGDownloader(output_dir=str(temp_dir))
        user_dir = downloader._create_output_directory("test_user")

        assert user_dir.exists()
        assert user_dir.is_dir()
        assert user_dir.name == "test_user"

        # 檢查 posts 子目錄是否建立
        posts_dir = user_dir / "posts"
        assert posts_dir.exists()
        assert posts_dir.is_dir()

    def test_create_output_directory_already_exists(self, temp_dir):
        """測試目錄已存在時的處理。"""
        # 先建立目錄
        user_dir = temp_dir / "test_user"
        user_dir.mkdir(parents=True, exist_ok=True)

        downloader = IGDownloader(output_dir=str(temp_dir))
        result_dir = downloader._create_output_directory("test_user")

        # 應該成功返回目錄路徑
        assert result_dir.exists()
        assert result_dir == user_dir


class TestReelIdentification:
    """測試 Reel 識別功能。"""

    def test_is_reel_with_product_type(self, temp_dir):
        """測試識別 Reel（使用 product_type）。

        需求：8.3 - THE IG Downloader SHALL 正確識別貼文是否為 Reel 類型
        """
        downloader = IGDownloader(output_dir=str(temp_dir))

        # 建立 mock post 物件
        mock_post = Mock()
        mock_post.product_type = "clips"

        assert downloader._is_reel(mock_post) is True

    def test_is_reel_not_reel(self, temp_dir):
        """測試識別非 Reel 貼文。"""
        downloader = IGDownloader(output_dir=str(temp_dir))

        # 建立 mock post 物件
        mock_post = Mock()
        mock_post.product_type = "feed"

        assert downloader._is_reel(mock_post) is False

    def test_is_reel_no_product_type(self, temp_dir):
        """測試沒有 product_type 屬性的貼文。"""
        downloader = IGDownloader(output_dir=str(temp_dir))

        # 建立 mock post 物件（沒有 product_type）
        mock_post = Mock(spec=[])

        assert downloader._is_reel(mock_post) is False
