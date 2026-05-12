"""
Generate a Markdown file that mirrors career_corner_videos.json.

Run after fetch_career_corner.py. The output (career_corner_videos.md)
is deterministic: same JSON in -> same Markdown out.
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

INPUT_FILE = Path("career_corner_videos.json")
OUTPUT_FILE = Path("career_corner_videos.md")


def parse_iso_duration(value: str) -> str:
    """Convert an ISO 8601 duration like PT1H2M3S to '1h 2m 3s'."""
    if not value or not value.startswith("PT"):
        return value or ""

    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", value)
    if not match:
        return value

    hours, minutes, seconds = match.groups()
    parts = []
    if hours:
        parts.append(f"{int(hours)}h")
    if minutes:
        parts.append(f"{int(minutes)}m")
    if seconds:
        parts.append(f"{int(seconds)}s")
    return " ".join(parts) if parts else value


def format_published(value: str) -> str:
    """YouTube returns ISO timestamps. Show just the date for readability."""
    if not value:
        return ""
    return value.split("T", 1)[0]


def render_video(video: Dict[str, Any]) -> str:
    title = video.get("title") or "(untitled)"
    video_url = video.get("video_url") or ""
    thumbnail_url = video.get("thumbnail_url") or ""
    description = (video.get("description") or "").strip()
    published = format_published(video.get("published_at", ""))
    duration = parse_iso_duration(video.get("duration", ""))
    channel = video.get("channel_title") or ""
    privacy = video.get("privacy_status") or ""
    video_id = video.get("video_id") or ""

    playlists: List[Dict[str, Any]] = video.get("playlists") or []
    transcript_available = bool(video.get("transcript_available"))
    transcript_type = video.get("transcript_type") or ""
    transcript_language = video.get("transcript_language") or ""
    transcript_text = (video.get("transcript") or "").strip()
    transcript_error = (video.get("transcript_error") or "").strip()

    lines: List[str] = []
    heading_title = f"[{title}]({video_url})" if video_url else title
    lines.append(f"## {heading_title}")
    lines.append("")

    if thumbnail_url:
        lines.append(f"![Thumbnail]({thumbnail_url})")
        lines.append("")

    meta_rows = [
        ("Video ID", f"`{video_id}`" if video_id else ""),
        ("Published", published),
        ("Duration", duration),
        ("Channel", channel),
        ("Privacy", privacy),
        ("Watch", f"[{video_url}]({video_url})" if video_url else ""),
    ]
    meta_rows = [(label, value) for label, value in meta_rows if value]
    if meta_rows:
        lines.append("| Field | Value |")
        lines.append("| --- | --- |")
        for label, value in meta_rows:
            lines.append(f"| {label} | {value} |")
        lines.append("")

    if playlists:
        lines.append("**Playlists:**")
        lines.append("")
        for playlist in playlists:
            pid = playlist.get("playlist_id", "")
            ptitle = playlist.get("playlist_title", "") or pid or "(unknown)"
            if pid:
                playlist_url = f"https://www.youtube.com/playlist?list={pid}"
                lines.append(f"- [{ptitle}]({playlist_url})")
            else:
                lines.append(f"- {ptitle}")
        lines.append("")

    if description:
        lines.append("### Description")
        lines.append("")
        lines.append(description)
        lines.append("")

    lines.append("### Transcript")
    lines.append("")
    if transcript_available and transcript_text:
        details = []
        if transcript_type:
            details.append(f"type: {transcript_type}")
        if transcript_language:
            details.append(f"language: {transcript_language}")
        if details:
            lines.append(f"_({', '.join(details)})_")
            lines.append("")
        lines.append(transcript_text)
    else:
        reason = transcript_error or "Transcript unavailable."
        lines.append(f"_{reason}_")
    lines.append("")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def render_document(dataset: Dict[str, Any]) -> str:
    videos: List[Dict[str, Any]] = dataset.get("videos") or []
    total = dataset.get("total_videos", len(videos))
    filter_text = (dataset.get("filter") or {}).get("title_contains", "")
    source = dataset.get("source", "YouTube")

    lines: List[str] = []
    lines.append("# Career Corner Videos")
    lines.append("")
    lines.append("> This file is generated from `career_corner_videos.json`. Do not edit by hand.")
    lines.append("")
    lines.append(f"- **Source:** {source}")
    if filter_text:
        lines.append(f"- **Title filter:** `{filter_text}`")
    lines.append(f"- **Total videos:** {total}")
    lines.append("")

    if videos:
        lines.append("## Index")
        lines.append("")
        for index, video in enumerate(videos, start=1):
            title = video.get("title") or "(untitled)"
            video_url = video.get("video_url") or ""
            if video_url:
                lines.append(f"{index}. [{title}]({video_url})")
            else:
                lines.append(f"{index}. {title}")
        lines.append("")

    lines.append("## Videos")
    lines.append("")
    for video in videos:
        lines.append(render_video(video))

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    if not INPUT_FILE.exists():
        print(f"Error: {INPUT_FILE} not found. Run fetch_career_corner.py first.", file=sys.stderr)
        return 1

    try:
        with INPUT_FILE.open("r", encoding="utf-8") as f:
            dataset = json.load(f)
    except json.JSONDecodeError as error:
        print(f"Error: {INPUT_FILE} is not valid JSON: {error}", file=sys.stderr)
        return 1

    markdown = render_document(dataset)
    OUTPUT_FILE.write_text(markdown, encoding="utf-8")

    video_count = len(dataset.get("videos") or [])
    print(f"Wrote {OUTPUT_FILE} ({video_count} videos, {len(markdown)} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
