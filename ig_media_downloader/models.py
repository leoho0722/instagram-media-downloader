"""Data models for IG Media Downloader."""

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class DownloadStats:
    """下載統計資訊 (Download statistics)."""

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
        """計算下載耗時 (Calculate download duration)."""
        return self.end_time - self.start_time

    @property
    def total_files(self) -> int:
        """計算總下載檔案數 (Calculate total downloaded files)."""
        return (
            self.downloaded_images
            + self.downloaded_videos
            + self.stories_downloaded
            + self.reels_downloaded
        )
