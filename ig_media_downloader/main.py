"""命令列介面 - Instagram 媒體下載工具的主程式入口點。"""

import argparse
import sys
from pathlib import Path

from instaloader.exceptions import (
    ConnectionException,
    ProfileNotExistsException,
    PrivateProfileNotFollowedException,
)

from .downloader import IGDownloader
from .logger import setup_logger
from .models import DownloadStats


def parse_arguments() -> argparse.Namespace:
    """解析命令列參數。

    Returns:
        argparse.Namespace: 解析後的參數物件

    需求：
        - 1.1: THE IG Downloader SHALL 接受一個 Instagram 帳號名稱作為輸入參數
        - 3.1: WHEN 開始下載時，THE IG Downloader SHALL 顯示目標帳號的基本資訊
    """
    parser = argparse.ArgumentParser(
        prog="ig-download",
        description="下載 Instagram 使用者的公開貼文媒體（圖片和影片）或單一貼文",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 下載使用者的所有貼文
  ig-download username

  # 下載使用者的貼文並包含 Stories 和 Reels
  ig-download username --include-stories --include-reels

  # 使用 4 個執行緒並行下載，限制最多 100 個貼文
  ig-download username --workers 4 --max-posts 100

  # 下載單一貼文（透過 URL）
  ig-download --url https://www.instagram.com/p/ABC123xyz/

  # 從 YAML 檔案批次下載多個貼文
  ig-download --url-file urls.yaml

  # 使用多執行緒批次下載
  ig-download --url-file urls.yaml --workers 4

  # 指定輸出目錄
  ig-download username --output-dir ~/Downloads/instagram
        """,
    )

    # 必填參數：使用者名稱（與 --url、--url-file 互斥）
    parser.add_argument(
        "username",
        type=str,
        nargs="?",
        help="Instagram 使用者名稱（帳號名稱）",
    )

    # 選填參數：單一貼文 URL
    parser.add_argument(
        "--url",
        type=str,
        help="Instagram 貼文 URL（與 username、--url-file 互斥）",
    )

    # 選填參數：URL 檔案
    parser.add_argument(
        "--url-file",
        type=str,
        help="包含多個 URL 的 YAML 檔案路徑（與 username、--url 互斥）",
    )

    # 選填參數：輸出目錄
    parser.add_argument(
        "--output-dir",
        type=str,
        default=".",
        help="下載檔案的輸出目錄（預設：當前目錄）",
    )

    # 選填參數：最大貼文數量
    parser.add_argument(
        "--max-posts",
        type=int,
        default=None,
        help="限制下載的貼文數量（預設：下載所有貼文）",
    )

    # 選填參數：是否下載 Stories
    parser.add_argument(
        "--include-stories",
        action="store_true",
        help="下載使用者的 Stories（限時動態）",
    )

    # 選填參數：是否下載 Reels
    parser.add_argument(
        "--include-reels",
        action="store_true",
        help="下載使用者的 Reels（短影片）",
    )

    # 選填參數：執行緒數量
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="並行下載的執行緒數量（預設：1，建議不超過 4）",
    )

    # 選填參數：是否啟用斷點續傳
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="停用斷點續傳功能（預設：啟用）",
    )

    args = parser.parse_args()

    # 驗證參數互斥性
    mode_count = sum([bool(args.username), bool(args.url), bool(args.url_file)])

    if mode_count == 0:
        parser.error("必須提供以下其中一個參數：username、--url 或 --url-file")
    elif mode_count > 1:
        parser.error("username、--url 和 --url-file 參數不能同時使用")

    # 驗證 Stories 和 Reels 選項只能用於下載使用者
    if (args.include_stories or args.include_reels) and not args.username:
        parser.error("--include-stories 和 --include-reels 只能與 username 一起使用")

    # 驗證 max_posts 選項只能用於下載使用者
    if args.max_posts and not args.username:
        parser.error("--max-posts 只能與 username 一起使用")

    return args


def display_summary(stats: DownloadStats) -> None:
    """顯示下載摘要統計。

    Args:
        stats: 下載統計資訊物件

    需求：
        - 3.3: THE IG Downloader SHALL 在每個媒體檔案下載完成後顯示確認訊息
        - 3.4: WHEN 所有下載完成時，THE IG Downloader SHALL 顯示下載摘要統計資訊
        - 3.5: THE IG Downloader SHALL 顯示下載的總檔案數量和儲存位置
    """
    print("\n" + "=" * 70)
    print("📊 下載摘要統計")
    print("=" * 70)
    print(f"使用者名稱: {stats.username}")
    print(f"輸出目錄: {stats.output_directory}")
    print("-" * 70)

    # 顯示下載的檔案統計
    print("一般貼文:")
    print(f"  • 總貼文數: {stats.total_posts}")
    print(f"  • 下載圖片: {stats.downloaded_images} 張")
    print(f"  • 下載影片: {stats.downloaded_videos} 個")
    print(f"  • 跳過檔案: {stats.skipped_files} 個")

    # 顯示 Stories 統計（如果有）
    if stats.stories_downloaded > 0:
        print("Stories:")
        print(f"  • 下載數量: {stats.stories_downloaded} 個")

    # 顯示 Reels 統計（如果有）
    if stats.reels_downloaded > 0:
        print("Reels:")
        print(f"  • 下載數量: {stats.reels_downloaded} 個")

    print("-" * 70)

    # 顯示總計
    print(f"總下載檔案數: {stats.total_files} 個")

    # 顯示錯誤數量（如果有）
    if stats.errors > 0:
        print(f"⚠️  錯誤數量: {stats.errors}")

    # 顯示是否為續傳模式
    if stats.resumed_from_previous:
        print("ℹ️  模式: 斷點續傳（從上次中斷處繼續）")

    # 顯示耗時
    duration = stats.duration
    hours = int(duration.total_seconds() // 3600)
    minutes = int((duration.total_seconds() % 3600) // 60)
    seconds = int(duration.total_seconds() % 60)

    if hours > 0:
        time_str = f"{hours} 小時 {minutes} 分鐘 {seconds} 秒"
    elif minutes > 0:
        time_str = f"{minutes} 分鐘 {seconds} 秒"
    else:
        time_str = f"{seconds} 秒"

    print(f"總耗時: {time_str}")
    print("=" * 70)

    # 顯示成功訊息
    if stats.total_files > 0:
        print("✅ 下載完成！")
    else:
        print("ℹ️  沒有下載任何新檔案（可能所有檔案都已存在）")

    print("=" * 70 + "\n")


def main() -> None:
    """主程式入口點。

    整合參數解析、下載器初始化和執行流程。

    需求：
        - 1.1: THE IG Downloader SHALL 接受一個 Instagram 帳號名稱作為輸入參數
        - 3.1: WHEN 開始下載時，THE IG Downloader SHALL 顯示目標帳號的基本資訊
        - 3.3: THE IG Downloader SHALL 在每個媒體檔案下載完成後顯示確認訊息
        - 3.4: WHEN 所有下載完成時，THE IG Downloader SHALL 顯示下載摘要統計資訊
        - 3.5: THE IG Downloader SHALL 顯示下載的總檔案數量和儲存位置
    """
    # 設定主程式的日誌記錄器
    logger = setup_logger("main")

    try:
        # 解析命令列參數
        args = parse_arguments()

        # 初始化下載器
        logger.info("初始化下載器...")
        downloader = IGDownloader(
            output_dir=args.output_dir,
            max_workers=args.workers,
            resume=not args.no_resume,
        )

        # 根據參數決定下載模式
        if args.url:
            # 模式 1: 下載單一貼文
            print("\n" + "=" * 70)
            print("📷 Instagram 媒體下載工具 - 單一貼文下載")
            print("=" * 70)
            print(f"貼文 URL: {args.url}")
            print(f"輸出目錄: {Path(args.output_dir).resolve()}")
            print("=" * 70 + "\n")

            logger.info(f"開始下載貼文: {args.url}")
            stats = downloader.download_post_from_url(args.url)

        elif args.url_file:
            # 模式 2: 批次下載多個貼文
            print("\n" + "=" * 70)
            print("📷 Instagram 媒體下載工具 - 批次下載")
            print("=" * 70)
            print(f"URL 檔案: {args.url_file}")
            print(f"輸出目錄: {Path(args.output_dir).resolve()}")

            # 顯示下載選項
            options = []
            if args.workers > 1:
                options.append(f"{args.workers} 個執行緒")
            if args.no_resume:
                options.append("停用斷點續傳")

            if options:
                print(f"下載選項: {', '.join(options)}")

            print("=" * 70 + "\n")

            # 讀取 URL 列表
            logger.info(f"從檔案讀取 URL: {args.url_file}")
            urls = downloader._read_urls_from_file(args.url_file)

            if not urls:
                print("⚠️  警告: 沒有找到有效的 URL", file=sys.stderr)
                sys.exit(1)

            # 開始批次下載
            logger.info(f"開始批次下載 {len(urls)} 個貼文")
            stats = downloader.download_posts_from_urls(urls)

            # 顯示失敗記錄檔案位置（如果有失敗）
            if stats.errors > 0:
                failed_file = Path(args.output_dir) / "failed_downloads.yaml"
                print(f"\n⚠️  有 {stats.errors} 個貼文下載失敗")
                print(f"失敗記錄已儲存到: {failed_file}\n")

        else:
            # 模式 3: 下載使用者的所有貼文
            print("\n" + "=" * 70)
            print("📷 Instagram 媒體下載工具")
            print("=" * 70)
            print(f"目標使用者: {args.username}")
            print(f"輸出目錄: {Path(args.output_dir).resolve()}")

            # 顯示下載選項
            options = []
            if args.include_stories:
                options.append("Stories")
            if args.include_reels:
                options.append("Reels")
            if args.max_posts:
                options.append(f"限制 {args.max_posts} 個貼文")
            if args.workers > 1:
                options.append(f"{args.workers} 個執行緒")
            if args.no_resume:
                options.append("停用斷點續傳")

            if options:
                print(f"下載選項: {', '.join(options)}")

            print("=" * 70 + "\n")

            # 開始下載
            logger.info(f"開始下載 {args.username} 的媒體...")
            stats = downloader.download_user_media(
                username=args.username,
                max_posts=args.max_posts,
                include_stories=args.include_stories,
                include_reels=args.include_reels,
            )

        # 顯示下載摘要
        display_summary(stats)

        # 正常結束
        sys.exit(0)

    except ValueError as e:
        # URL 格式錯誤或 YAML 格式錯誤
        print("\n❌ 錯誤: 格式錯誤", file=sys.stderr)
        print(str(e), file=sys.stderr)
        print("請檢查 URL 或檔案格式是否正確。\n", file=sys.stderr)
        logger.error("格式錯誤: %s", e)
        sys.exit(1)

    except FileNotFoundError as e:
        # 檔案不存在
        print("\n❌ 錯誤: 檔案不存在", file=sys.stderr)
        print(str(e), file=sys.stderr)
        print("請檢查檔案路徑是否正確。\n", file=sys.stderr)
        logger.error("檔案不存在: %s", e)
        sys.exit(1)

    except ProfileNotExistsException:
        # 帳號不存在
        print("\n❌ 錯誤: 帳號不存在", file=sys.stderr)
        if args.username:
            print(f"找不到 Instagram 帳號: {args.username}", file=sys.stderr)
        else:
            print("找不到 Instagram 帳號或貼文", file=sys.stderr)
        print("請檢查帳號名稱或 URL 是否正確。\n", file=sys.stderr)
        logger.error("帳號不存在")
        sys.exit(1)

    except PrivateProfileNotFollowedException:
        # 私人帳號
        print("\n❌ 錯誤: 私人帳號", file=sys.stderr)
        if args.username:
            print(f"帳號 {args.username} 是私人帳號，無法下載。", file=sys.stderr)
        else:
            print("該貼文來自私人帳號，無法下載。", file=sys.stderr)
        print("此工具目前僅支援公開帳號。\n", file=sys.stderr)
        logger.error("私人帳號")
        sys.exit(1)

    except ConnectionException as e:
        # 網路連線錯誤
        print("\n❌ 錯誤: 網路連線失敗", file=sys.stderr)
        print(f"無法連接到 Instagram: {e}", file=sys.stderr)
        print("請檢查網路連線並稍後再試。\n", file=sys.stderr)
        logger.error("網路連線失敗: %s", e)
        sys.exit(1)

    except PermissionError as e:
        # 權限不足
        print("\n❌ 錯誤: 檔案權限不足", file=sys.stderr)
        print(str(e), file=sys.stderr)
        print("請檢查輸出目錄的寫入權限。\n", file=sys.stderr)
        logger.error("權限不足: %s", e)
        sys.exit(1)

    except OSError as e:
        # 磁碟空間不足或其他檔案系統錯誤
        if e.errno == 28:  # ENOSPC
            print("\n❌ 錯誤: 磁碟空間不足", file=sys.stderr)
            print("請釋放磁碟空間後再試。\n", file=sys.stderr)
            logger.error("磁碟空間不足")
        else:
            print("\n❌ 錯誤: 檔案系統錯誤", file=sys.stderr)
            print(f"{e}\n", file=sys.stderr)
            logger.error("檔案系統錯誤: %s", e)
        sys.exit(1)

    except KeyboardInterrupt:
        # 使用者中斷
        print("\n\n⚠️  下載已被使用者中斷", file=sys.stderr)
        print("下載進度已儲存，下次執行時可以從中斷處繼續。\n", file=sys.stderr)
        logger.info("下載被使用者中斷")
        sys.exit(130)

    except Exception as e:
        # 其他未預期的錯誤
        print("\n❌ 錯誤: 發生未預期的錯誤", file=sys.stderr)
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
        print("請查看日誌檔案以獲取更多資訊。\n", file=sys.stderr)
        logger.exception("發生未預期的錯誤")
        sys.exit(1)


if __name__ == "__main__":
    main()
