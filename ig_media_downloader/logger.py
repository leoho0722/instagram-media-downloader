"""日誌系統模組 - 提供統一的日誌記錄功能。"""

import logging
import sys
from pathlib import Path


def setup_logger(
    name: str, log_file: str = "ig_downloader.log", level: int = logging.INFO
) -> logging.Logger:
    """設定日誌記錄器，配置檔案和控制台輸出。

    Args:
        name: 日誌記錄器名稱
        log_file: 日誌檔案路徑，預設為 "ig_downloader.log"
        level: 日誌等級，預設為 INFO

    Returns:
        配置完成的 Logger 實例

    需求：4.5 - THE IG Downloader SHALL 記錄所有錯誤到日誌檔案中以供除錯使用
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 避免重複添加 handler
    if logger.handlers:
        return logger

    # 日誌格式：時間 - 等級 - 訊息
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 檔案處理器 - 記錄所有等級的日誌
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 控制台處理器 - 只顯示 INFO 及以上等級
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
