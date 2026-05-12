import json
import os
import sys
import time
import traceback
from typing import Dict, List

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)


load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID")
CAREER_CORNER_PLAYLIST_ID = os.getenv("CAREER_CORNER_PLAYLIST_ID", "").strip()

FILTER_TEXT = "Career Corner"
OUTPUT_FILE = "career_corner_videos.json"


def get_youtube_client():
    if not YOUTUBE_API_KEY:
        raise ValueError("Missing YOUTUBE_API_KEY in your .env file.")

    return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


def get_all_channel_playlists(youtube) -> List[Dict]:
    """
    Pulls all public playlists from the channel.
    """
    playlists = []
    next_page_token = None

    while True:
        request = youtube.playlists().list(
            part="snippet,contentDetails",
            channelId=YOUTUBE_CHANNEL_ID,
            maxResults=50,
            pageToken=next_page_token,
        )
        response = request.execute()

        for item in response.get("items", []):
            playlists.append(
                {
                    "playlist_id": item["id"],
                    "playlist_title": item["snippet"].get("title", ""),
                    "playlist_description": item["snippet"].get("description", ""),
                    "video_count": item.get("contentDetails", {}).get("itemCount", 0),
                }
            )

        next_page_token = response.get("nextPageToken")

        if not next_page_token:
            break

        time.sleep(0.1)

    return playlists


def get_playlist_items(youtube, playlist_id: str, playlist_title: str) -> List[Dict]:
    """
    Gets all videos inside one playlist.
    """
    videos = []
    next_page_token = None

    while True:
        request = youtube.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page_token,
        )
        response = request.execute()

        for item in response.get("items", []):
            snippet = item.get("snippet", {})
            resource_id = snippet.get("resourceId", {})

            video_id = resource_id.get("videoId") or item.get("contentDetails", {}).get("videoId")

            if not video_id:
                continue

            videos.append(
                {
                    "video_id": video_id,
                    "playlist_id": playlist_id,
                    "playlist_title": playlist_title,
                }
            )

        next_page_token = response.get("nextPageToken")

        if not next_page_token:
            break

        time.sleep(0.1)

    return videos


def get_video_metadata(youtube, video_ids: List[str]) -> Dict[str, Dict]:
    """
    Gets title, description, thumbnails, publish date, and other metadata.
    YouTube allows up to 50 video IDs per videos.list request.
    """
    metadata = {}

    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i : i + 50]

        request = youtube.videos().list(
            part="snippet,contentDetails,status",
            id=",".join(chunk),
            maxResults=50,
        )
        response = request.execute()

        for item in response.get("items", []):
            video_id = item["id"]
            snippet = item.get("snippet", {})
            thumbnails = snippet.get("thumbnails", {})

            best_thumbnail = (
                thumbnails.get("maxres")
                or thumbnails.get("standard")
                or thumbnails.get("high")
                or thumbnails.get("medium")
                or thumbnails.get("default")
                or {}
            )

            metadata[video_id] = {
                "video_id": video_id,
                "title": snippet.get("title", ""),
                "description": snippet.get("description", ""),
                "published_at": snippet.get("publishedAt", ""),
                "channel_title": snippet.get("channelTitle", ""),
                "thumbnail_url": best_thumbnail.get("url", ""),
                "video_url": f"https://www.youtube.com/watch?v={video_id}",
                "privacy_status": item.get("status", {}).get("privacyStatus", ""),
                "duration": item.get("contentDetails", {}).get("duration", ""),
            }

        time.sleep(0.1)

    return metadata


def get_transcript(video_id: str) -> Dict:
    """
    Attempts to fetch a transcript for the video.
    Returns transcript text and basic transcript status info.

    Note:
    This works when transcripts/captions are available.
    Some videos may have transcripts disabled or unavailable.
    """
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        transcript = None

        try:
            transcript = transcript_list.find_manually_created_transcript(["en"])
            transcript_type = "manual"
        except NoTranscriptFound:
            transcript = transcript_list.find_generated_transcript(["en"])
            transcript_type = "auto_generated"

        transcript_data = transcript.fetch()

        transcript_text = " ".join(
            [entry.get("text", "").replace("\n", " ").strip() for entry in transcript_data]
        ).strip()

        return {
            "transcript_available": True,
            "transcript_type": transcript_type,
            "transcript_language": transcript.language,
            "transcript_language_code": transcript.language_code,
            "transcript": transcript_text,
            "transcript_segments": transcript_data,
        }

    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable) as error:
        return {
            "transcript_available": False,
            "transcript_type": None,
            "transcript_language": None,
            "transcript_language_code": None,
            "transcript": "",
            "transcript_segments": [],
            "transcript_error": str(error),
        }

    except Exception as error:
        return {
            "transcript_available": False,
            "transcript_type": None,
            "transcript_language": None,
            "transcript_language_code": None,
            "transcript": "",
            "transcript_segments": [],
            "transcript_error": f"Unexpected transcript error: {error}",
        }


def dedupe_videos(videos: List[Dict]) -> List[Dict]:
    """
    If a video appears in multiple playlists, keep the video but merge playlist data.
    """
    video_map = {}

    for video in videos:
        video_id = video["video_id"]

        playlist_data = {
            "playlist_id": video["playlist_id"],
            "playlist_title": video["playlist_title"],
        }

        if video_id not in video_map:
            video_map[video_id] = {
                "video_id": video_id,
                "playlists": [playlist_data],
            }
        else:
            existing_playlist_ids = {
                playlist["playlist_id"] for playlist in video_map[video_id]["playlists"]
            }

            if playlist_data["playlist_id"] not in existing_playlist_ids:
                video_map[video_id]["playlists"].append(playlist_data)

    return list(video_map.values())


def _mask(value: str) -> str:
    if not value:
        return "(empty)"
    if len(value) <= 6:
        return "*" * len(value)
    return f"{value[:3]}...{value[-3:]} (len={len(value)})"


def validate_config():
    print("Config check:")
    print(f"  YOUTUBE_API_KEY: {_mask(YOUTUBE_API_KEY or '')}")
    print(f"  YOUTUBE_CHANNEL_ID: {YOUTUBE_CHANNEL_ID or '(empty)'}")
    print(
        f"  CAREER_CORNER_PLAYLIST_ID: {CAREER_CORNER_PLAYLIST_ID or '(empty, will scan all playlists)'}"
    )

    if not YOUTUBE_API_KEY:
        raise ValueError(
            "Missing YOUTUBE_API_KEY. Set it as a GitHub Actions secret named "
            "YOUTUBE_API_KEY (or in a local .env file)."
        )

    if not YOUTUBE_CHANNEL_ID and not CAREER_CORNER_PLAYLIST_ID:
        raise ValueError(
            "Missing both YOUTUBE_CHANNEL_ID and CAREER_CORNER_PLAYLIST_ID. "
            "Set at least one as a GitHub Actions secret."
        )


def build_career_corner_dataset():
    validate_config()

    youtube = get_youtube_client()

    all_playlist_videos = []

    if CAREER_CORNER_PLAYLIST_ID:
        print(f"Using Career Corner playlist ID: {CAREER_CORNER_PLAYLIST_ID}")

        all_playlist_videos.extend(
            get_playlist_items(
                youtube=youtube,
                playlist_id=CAREER_CORNER_PLAYLIST_ID,
                playlist_title="Career Corner",
            )
        )

    else:
        print("No CAREER_CORNER_PLAYLIST_ID found. Scanning all channel playlists...")

        playlists = get_all_channel_playlists(youtube)

        print(f"Found {len(playlists)} playlists.")

        for playlist in playlists:
            playlist_id = playlist["playlist_id"]
            playlist_title = playlist["playlist_title"]

            print(f"Scanning playlist: {playlist_title}")

            playlist_videos = get_playlist_items(
                youtube=youtube,
                playlist_id=playlist_id,
                playlist_title=playlist_title,
            )

            all_playlist_videos.extend(playlist_videos)

    deduped_videos = dedupe_videos(all_playlist_videos)

    print(f"Found {len(deduped_videos)} unique videos before filtering.")

    video_ids = [video["video_id"] for video in deduped_videos]
    metadata_by_id = get_video_metadata(youtube, video_ids)

    career_corner_videos = []

    for video in deduped_videos:
        video_id = video["video_id"]
        metadata = metadata_by_id.get(video_id)

        if not metadata:
            continue

        title = metadata.get("title", "")

        if FILTER_TEXT.lower() not in title.lower():
            continue

        print(f"Fetching transcript: {title}")

        transcript_data = get_transcript(video_id)

        career_corner_videos.append(
            {
                "video_id": video_id,
                "title": metadata.get("title", ""),
                "description": metadata.get("description", ""),
                "video_url": metadata.get("video_url", ""),
                "thumbnail_url": metadata.get("thumbnail_url", ""),
                "published_at": metadata.get("published_at", ""),
                "duration": metadata.get("duration", ""),
                "channel_title": metadata.get("channel_title", ""),
                "privacy_status": metadata.get("privacy_status", ""),
                "playlists": video.get("playlists", []),
                "filter_match": FILTER_TEXT,
                "transcript_available": transcript_data.get("transcript_available", False),
                "transcript_type": transcript_data.get("transcript_type"),
                "transcript_language": transcript_data.get("transcript_language"),
                "transcript_language_code": transcript_data.get("transcript_language_code"),
                "transcript": transcript_data.get("transcript", ""),
                "transcript_segments": transcript_data.get("transcript_segments", []),
                "transcript_error": transcript_data.get("transcript_error", ""),
            }
        )

        time.sleep(0.2)

    dataset = {
        "source": "YouTube",
        "filter": {
            "title_contains": FILTER_TEXT,
        },
        "total_videos": len(career_corner_videos),
        "videos": career_corner_videos,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(dataset, file, indent=2, ensure_ascii=False)

    print(f"Done. Saved {len(career_corner_videos)} videos to {OUTPUT_FILE}")


if __name__ == "__main__":
    try:
        build_career_corner_dataset()
    except HttpError as error:
        print(f"YouTube API error: {error}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
