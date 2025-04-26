import argparse
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from loguru import logger
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from dotenv import load_dotenv
from dotenv import load_dotenv

PR_REGEX = re.compile(r"(\bPR\b|\b案件\b|\b提供\b|\bタイアップ\b|#PR|#提供|sponsored|paid promotion)", re.IGNORECASE)


def parse_args():
    parser = argparse.ArgumentParser(description="YouTube PR動画抽出＋文字起こしツール")
    parser.add_argument("--channel", required=True, help="YouTubeチャンネルID (UCxxxxxx)")
    parser.add_argument("--api-key", required=False, help="YouTube Data API v3 キー（省略時は.envから取得）")
    parser.add_argument("--max-videos", type=int, default=None, help="取得上限（デバッグ用）")
    parser.add_argument("--output", default="output", help="出力ディレクトリ (既定: ./output)")
    parser.add_argument("--debug", action="store_true", help="ログレベル=DEBUG")
    return parser.parse_args()


def setup_logger(output_dir, debug):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    log_level = "DEBUG" if debug else "INFO"
    now = datetime.now().strftime("%Y%m%d_%H%M")
    log_path = Path(output_dir) / f"../logs/run_{now}.log"
    logger.remove()
    logger.add(sys.stderr, level=log_level)
    logger.add(log_path, level=log_level, encoding="utf-8")
    return log_path


def get_uploads_playlist_id(youtube, channel_id):
    resp = youtube.channels().list(part="contentDetails", id=channel_id).execute()
    items = resp.get("items", [])
    if not items:
        raise ValueError(f"チャンネルIDが不正または存在しません: {channel_id}")
    return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]


def get_all_video_ids(youtube, playlist_id, max_videos=None):
    video_ids = []
    next_page = None
    while True:
        req = youtube.playlistItems().list(
            part="contentDetails",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page
        )
        resp = req.execute()
        for item in resp.get("items", []):
            video_ids.append(item["contentDetails"]["videoId"])
            if max_videos and len(video_ids) >= max_videos:
                return video_ids[:max_videos]
        next_page = resp.get("nextPageToken")
        if not next_page or (max_videos and len(video_ids) >= max_videos):
            break
    return video_ids


def batch_get_videos(youtube, video_ids):
    meta = []
    for i in range(0, len(video_ids), 50):
        ids = video_ids[i:i+50]
        resp = youtube.videos().list(
            part="snippet,contentDetails",
            id=",".join(ids)
        ).execute()
        meta.extend(resp.get("items", []))
    return meta


def is_pr_video(snippet):
    fields = [snippet.get("title", ""), snippet.get("description", "")]
    tags = snippet.get("tags", [])
    if tags:
        fields.extend(tags)
    for field in fields:
        m = PR_REGEX.search(str(field))
        if m:
            return True, m.group(0)
    return False, ""


def get_caption(video_id):
    try:
        transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
        for lang in ["ja", "en"]:
            if transcripts.find_generated_transcript([lang]):
                t = transcripts.find_generated_transcript([lang])
                return " ".join([x["text"] for x in t.fetch()])
    except (TranscriptsDisabled, NoTranscriptFound):
        logger.warning(f"字幕取得失敗: {video_id}")
        return ""
    except Exception as e:
        logger.warning(f"字幕取得例外: {video_id} {e}")
        return ""
    return ""


def exponential_backoff(func, *args, max_retries=5, **kwargs):
    delay = 2
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except HttpError as e:
            if e.resp.status in [403, 429]:
                logger.warning(f"Quota/403エラー: {e}. {delay}s 待機 (試行{attempt+1})")
                time.sleep(delay)
                delay *= 2
            else:
                raise
    raise RuntimeError("APIクオータ超過または403が継続")


def main():
    load_dotenv()
    args = parse_args()
    # --api-key未指定時は環境変数を参照
    api_key = args.api_key or os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        logger.error("APIキーが指定されていません (--api-key または .env の YOUTUBE_API_KEY)")
        sys.exit(1)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = setup_logger(output_dir, args.debug)
    logger.info(f"ログ: {log_path}")
    try:
        youtube = build("youtube", "v3", developerKey=api_key)
        uploads_id = exponential_backoff(get_uploads_playlist_id, youtube, args.channel)
        logger.info(f"uploads プレイリストID: {uploads_id}")
        video_ids = exponential_backoff(get_all_video_ids, youtube, uploads_id, args.max_videos)
        logger.info(f"動画件数: {len(video_ids)}")
        videos = exponential_backoff(batch_get_videos, youtube, video_ids)
        logger.info(f"メタ情報取得: {len(videos)}件")
        # まずPR判定だけ先に実施
        pr_videos = []
        for v in videos:
            snippet = v.get("snippet", {})
            video_id = v["id"]
            published_at = snippet.get("publishedAt", "")
            title = snippet.get("title", "")
            description = snippet.get("description", "")
            is_pr, pr_keyword = is_pr_video(snippet)
            if is_pr:
                pr_videos.append({
                    "video_id": video_id,
                    "published_at": published_at,
                    "title": title,
                    "description": description,
                    "snippet": snippet,
                    "pr_keyword_hit": pr_keyword
                })

        logger.info(f"PR動画件数: {len(pr_videos)}")

        # PR動画だけ字幕取得
        def extract_sponsor_and_product(description):
            import re
            sponsor = ""
            product = ""
            # 提供会社
            sponsor_match = re.search(r'提供[:：]?([\w\u3000-\u9FFF\uFF01-\uFF5E\s]+)', description)
            if sponsor_match:
                sponsor = sponsor_match.group(1).strip()
            # 商品名
            product_match = re.search(r'(商品名|アイテム名)[:：]?([\w\u3000-\u9FFF\uFF01-\uFF5E\s]+)', description)
            if product_match:
                product = product_match.group(2).strip()
            return sponsor, product

        rows = []
        for pr in pr_videos:
            caption = get_caption(pr["video_id"])
            sponsor, product = extract_sponsor_and_product(pr["description"])
            video_url = f"https://www.youtube.com/watch?v={pr['video_id']}"
            rows.append({
                "video_id": pr["video_id"],
                "published_at": pr["published_at"],
                "title": pr["title"],
                "description": pr["description"],
                "caption": caption,
                "is_pr": True,
                "pr_keyword_hit": pr["pr_keyword_hit"],
                "sponsor": sponsor,
                "product": product,
                "video_url": video_url
            })
        df = pd.DataFrame(rows)
        out_path = output_dir / "pr_videos.csv"
        df.to_csv(out_path, index=False, encoding="utf-8")
        logger.info(f"CSV出力: {out_path}")
    except Exception as e:
        logger.exception(f"致命的エラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
