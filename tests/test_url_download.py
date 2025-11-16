"""測試 URL 下載功能。"""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from ig_media_downloader.downloader import IGDownloader


class TestURLParsing:
    """測試 URL 解析功能。"""

    def test_extract_shortcode_from_post_url(self, temp_dir):
        """測試從貼文 URL 提取 shortcode。

        需求：10.2 - WHEN 使用者提供貼文 URL 時，THE IG Downloader SHALL 從 URL 中提取貼文的 shortcode
        """
        downloader = IGDownloader(output_dir=str(temp_dir))

        url = "https://www.instagram.com/p/ABC123xyz/"
        shortcode = downloader._extract_shortcode_from_url(url)

        assert shortcode == "ABC123xyz"

    def test_extract_shortcode_from_reel_url(self, temp_dir):
        """測試從 Reel URL 提取 shortcode。"""
        downloader = IGDownloader(output_dir=str(temp_dir))

        url = "https://www.instagram.com/reel/XYZ789abc/"
        shortcode = downloader._extract_shortcode_from_url(url)

        assert shortcode == "XYZ789abc"

    def test_extract_shortcode_without_www(self, temp_dir):
        """測試不含 www 的 URL。"""
        downloader = IGDownloader(output_dir=str(temp_dir))

        url = "https://instagram.com/p/ABC123xyz/"
        shortcode = downloader._extract_shortcode_from_url(url)

        assert shortcode == "ABC123xyz"

    def test_extract_shortcode_http(self, temp_dir):
        """測試 HTTP 協議的 URL。"""
        downloader = IGDownloader(output_dir=str(temp_dir))

        url = "http://www.instagram.com/p/ABC123xyz/"
        shortcode = downloader._extract_shortcode_from_url(url)

        assert shortcode == "ABC123xyz"

    def test_extract_shortcode_invalid_url(self, temp_dir):
        """測試無效的 URL 格式。

        需求：10.5 - IF 貼文 URL 格式不正確，THEN THE IG Downloader SHALL 顯示錯誤訊息並終止執行
        """
        downloader = IGDownloader(output_dir=str(temp_dir))

        with pytest.raises(ValueError, match="無效的 Instagram URL 格式"):
            downloader._extract_shortcode_from_url("https://example.com/invalid")


class TestSinglePostDownload:
    """測試單一貼文下載功能。"""

    @patch("ig_media_downloader.downloader.instaloader.Post")
    def test_download_post_from_shortcode(self, mock_post_class, temp_dir):
        """測試從 shortcode 下載貼文。

        需求：10.3 - THE IG Downloader SHALL 使用 shortcode 擷取該貼文的資訊
        需求：10.4 - THE IG Downloader SHALL 下載該貼文中的所有媒體檔案（圖片或影片）
        """
        downloader = IGDownloader(output_dir=str(temp_dir))

        # 建立 mock post
        mock_post = Mock()
        mock_post.shortcode = "ABC123"
        mock_post.owner_username = "test_user"
        mock_post.date_local = datetime(2024, 1, 16, 10, 0, 0)
        mock_post.is_video = False
        mock_post.typename = "GraphImage"

        mock_post_class.from_shortcode.return_value = mock_post

        # Mock _download_post 方法
        with patch.object(downloader, "_download_post", return_value=(1, 0, 0)):
            stats = downloader.download_post_from_shortcode("ABC123")

        assert stats.username == "test_user"
        assert stats.total_posts == 1
        assert stats.downloaded_images == 1

    @patch("ig_media_downloader.downloader.instaloader.Post")
    def test_download_post_from_url(self, mock_post_class, temp_dir):
        """測試從 URL 下載貼文。

        需求：10.1 - THE IG Downloader SHALL 接受 Instagram 貼文 URL 作為輸入參數
        """
        downloader = IGDownloader(output_dir=str(temp_dir))

        # 建立 mock post
        mock_post = Mock()
        mock_post.shortcode = "ABC123"
        mock_post.owner_username = "test_user"
        mock_post.date_local = datetime(2024, 1, 16, 10, 0, 0)
        mock_post.is_video = False
        mock_post.typename = "GraphImage"

        mock_post_class.from_shortcode.return_value = mock_post

        # Mock _download_post 方法
        with patch.object(downloader, "_download_post", return_value=(1, 0, 0)):
            stats = downloader.download_post_from_url(
                "https://www.instagram.com/p/ABC123/"
            )

        assert stats.username == "test_user"
        assert stats.total_posts == 1


class TestBatchDownload:
    """測試批次下載功能。"""

    def test_read_urls_from_yaml_simple_format(self, temp_dir):
        """測試讀取簡化格式的 YAML 檔案。"""
        downloader = IGDownloader(output_dir=str(temp_dir))

        # 建立測試 YAML 檔案
        yaml_file = temp_dir / "urls.yaml"
        yaml_content = """
urls:
  - https://www.instagram.com/p/ABC123/
  - https://www.instagram.com/p/DEF456/
"""
        yaml_file.write_text(yaml_content)

        urls = downloader._read_urls_from_file(str(yaml_file))

        assert len(urls) == 2
        assert "https://www.instagram.com/p/ABC123/" in urls
        assert "https://www.instagram.com/p/DEF456/" in urls

    def test_read_urls_from_yaml_detailed_format(self, temp_dir):
        """測試讀取詳細格式的 YAML 檔案。"""
        downloader = IGDownloader(output_dir=str(temp_dir))

        # 建立測試 YAML 檔案
        yaml_file = temp_dir / "urls.yaml"
        yaml_content = """
urls:
  - url: https://www.instagram.com/p/ABC123/
    description: "Test post 1"
  - url: https://www.instagram.com/p/DEF456/
    description: "Test post 2"
"""
        yaml_file.write_text(yaml_content)

        urls = downloader._read_urls_from_file(str(yaml_file))

        assert len(urls) == 2
        assert "https://www.instagram.com/p/ABC123/" in urls

    def test_read_urls_invalid_yaml(self, temp_dir):
        """測試讀取無效的 YAML 檔案。"""
        downloader = IGDownloader(output_dir=str(temp_dir))

        # 建立無效的 YAML 檔案
        yaml_file = temp_dir / "invalid.yaml"
        yaml_file.write_text("{ invalid yaml }")

        with pytest.raises(ValueError, match="YAML 檔案格式錯誤"):
            downloader._read_urls_from_file(str(yaml_file))

    def test_read_urls_file_not_found(self, temp_dir):
        """測試讀取不存在的檔案。"""
        downloader = IGDownloader(output_dir=str(temp_dir))

        with pytest.raises(FileNotFoundError):
            downloader._read_urls_from_file(str(temp_dir / "nonexistent.yaml"))
