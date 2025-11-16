"""測試資料模型 - DownloadStats。"""

from datetime import datetime, timedelta

import pytest

from ig_media_downloader.models import DownloadStats


class TestDownloadStats:
    """測試 DownloadStats 資料模型。"""

    def test_duration_property(self):
        """測試 duration 屬性計算下載耗時。

        需求：2.4 - THE IG Downloader SHALL 保留媒體檔案的原始檔名或使用有意義的命名規則
        """
        start_time = datetime(2024, 1, 16, 10, 0, 0)
        end_time = datetime(2024, 1, 16, 10, 5, 30)

        stats = DownloadStats(
            username="test_user",
            total_posts=10,
            downloaded_images=5,
            downloaded_videos=3,
            skipped_files=2,
            errors=0,
            output_directory="/tmp/test",
            start_time=start_time,
            end_time=end_time,
        )

        expected_duration = timedelta(minutes=5, seconds=30)
        assert stats.duration == expected_duration

    def test_total_files_property(self):
        """測試 total_files 屬性計算總下載檔案數。

        需求：2.4 - THE IG Downloader SHALL 保留媒體檔案的原始檔名或使用有意義的命名規則
        """
        stats = DownloadStats(
            username="test_user",
            total_posts=10,
            downloaded_images=5,
            downloaded_videos=3,
            skipped_files=2,
            errors=0,
            output_directory="/tmp/test",
            start_time=datetime.now(),
            end_time=datetime.now(),
            stories_downloaded=2,
            reels_downloaded=1,
        )

        # total_files = downloaded_images + downloaded_videos + stories_downloaded + reels_downloaded
        # = 5 + 3 + 2 + 1 = 11
        assert stats.total_files == 11

    def test_total_files_without_stories_and_reels(self):
        """測試沒有 Stories 和 Reels 時的總檔案數。"""
        stats = DownloadStats(
            username="test_user",
            total_posts=10,
            downloaded_images=5,
            downloaded_videos=3,
            skipped_files=2,
            errors=0,
            output_directory="/tmp/test",
            start_time=datetime.now(),
            end_time=datetime.now(),
        )

        # total_files = downloaded_images + downloaded_videos
        # = 5 + 3 = 8
        assert stats.total_files == 8
