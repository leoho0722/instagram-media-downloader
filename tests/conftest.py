"""Pytest 配置檔案 - 提供測試用的 fixtures。"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """建立臨時目錄用於測試。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_progress_data():
    """提供範例進度資料。"""
    return {
        "username": "test_user",
        "last_updated": "2024-01-16T10:30:00",
        "downloaded_posts": ["ABC123", "XYZ789"],
        "downloaded_reels": ["REEL001"],
    }


@pytest.fixture
def create_progress_file(temp_dir, sample_progress_data):
    """建立測試用的進度檔案。"""

    def _create(username="test_user", data=None):
        user_dir = temp_dir / username
        user_dir.mkdir(parents=True, exist_ok=True)
        progress_file = user_dir / ".download_progress.json"

        if data is None:
            data = sample_progress_data

        with open(progress_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

        return progress_file

    return _create
