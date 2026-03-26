"""
Upload a single video to YouTube — standalone one-off uploader for content-empire.
Uses YouTube Data API v3 with OAuth2 refresh token stored as env vars.
"""
import os
import sys
import time
import argparse

import google.oauth2.credentials
import googleapiclient.discovery
import googleapiclient.http
from googleapiclient.errors import HttpError

RETRYABLE_STATUS_CODES = {429, 500, 503}
MAX_RETRIES = 3
RETRY_SLEEP_SECONDS = 30


def check_credentials():
    """Verify required YouTube OAuth env vars are set. Exit(0) with clear message if not."""
    required = ["YOUTUBE_REFRESH_TOKEN", "YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET"]
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        print(
            "⚠️ YouTube credentials not configured. "
            "Set YOUTUBE_REFRESH_TOKEN, YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET secrets."
        )
        sys.exit(0)


def get_youtube_client():
    """Build authenticated YouTube client from stored refresh token."""
    creds = google.oauth2.credentials.Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
    )
    return googleapiclient.discovery.build("youtube", "v3", credentials=creds)


def upload_video(youtube, video_path: str, title: str, description: str, playlist_id: str = ""):
    """Upload a single video to YouTube with retry on transient errors."""
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "categoryId": "28",  # Science & Technology
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    print(f"Uploading: {video_path}")
    print(f"  Title: {title}")

    for attempt in range(1, MAX_RETRIES + 1):
        media = googleapiclient.http.MediaFileUpload(
            video_path,
            mimetype="video/mp4",
            resumable=True,
            chunksize=1024 * 1024 * 5,  # 5 MB chunks
        )
        try:
            request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    print(f"  Progress: {int(status.progress() * 100)}%")

            video_id = response["id"]
            video_url = f"https://youtu.be/{video_id}"
            print(f"✅ Uploaded: {video_url}")

            if playlist_id:
                youtube.playlistItems().insert(
                    part="snippet",
                    body={
                        "snippet": {
                            "playlistId": playlist_id,
                            "resourceId": {"kind": "youtube#video", "videoId": video_id},
                        }
                    },
                ).execute()
                print(f"📋 Added to playlist: {playlist_id}")

            return video_id

        except HttpError as e:
            if e.resp.status in RETRYABLE_STATUS_CODES and attempt < MAX_RETRIES:
                print(
                    f"⚠️ Transient error (HTTP {e.resp.status}) on attempt {attempt}/{MAX_RETRIES}. "
                    f"Retrying in {RETRY_SLEEP_SECONDS}s..."
                )
                time.sleep(RETRY_SLEEP_SECONDS)
            else:
                raise


def main():
    check_credentials()

    parser = argparse.ArgumentParser(description="Upload a video to YouTube")
    parser.add_argument("--video", required=True, help="Path to video file")
    parser.add_argument("--title", required=True, help="YouTube video title")
    parser.add_argument("--description", default="", help="YouTube video description")
    parser.add_argument("--playlist-id", default="", help="YouTube playlist ID (optional)")
    args = parser.parse_args()

    if not os.path.exists(args.video):
        print(f"❌ Video file not found: {args.video}")
        sys.exit(1)

    youtube = get_youtube_client()
    upload_video(youtube, args.video, args.title, args.description, args.playlist_id)


if __name__ == "__main__":
    main()
