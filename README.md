# YouTube Career Corner Bot Data Exporter

This repo pulls videos from a YouTube channel or playlist, filters for videos with **"Career Corner"** in the title, grabs available transcripts, and exports everything into a JSON file that can be used by a chatbot or knowledge base.

## What it exports

Each video includes:

- Video title
- Video description
- YouTube video link
- Thumbnail link
- Playlist information
- Transcript
- Transcript segments
- Published date
- Duration
- Video ID

## How filtering works

The script filters by title, not only playlist name.

That means it will continue working later even if Career Corner videos are spread across multiple playlists, as long as the video title contains:

```text
Career Corner
```

Recommended title format:

```text
Career Corner: Resume Tips for Students
Career Corner: Interview Prep
Career Corner: How to Use Handshake
```

## Setup

### 1. Clone this repo

```bash
git clone https://github.com/YOUR-USERNAME/youtube-career-corner-bot-data.git
cd youtube-career-corner-bot-data
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it:

Mac/Linux:

```bash
source venv/bin/activate
```

Windows:

```bash
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create your `.env` file

Copy the example file:

```bash
cp .env.example .env
```

Then update it:

```env
YOUTUBE_API_KEY=your_youtube_data_api_key_here
YOUTUBE_CHANNEL_ID=your_channel_id_here
CAREER_CORNER_PLAYLIST_ID=
```

If all Career Corner videos are currently in one playlist, add that playlist ID to make the script faster:

```env
CAREER_CORNER_PLAYLIST_ID=your_playlist_id_here
```

If you leave `CAREER_CORNER_PLAYLIST_ID` blank, the script scans all public playlists on the channel and still filters videos by titles containing `Career Corner`.

## Run the script

```bash
python fetch_career_corner.py
```

The script will create:

```text
career_corner_videos.json
```

## Example JSON output

```json
{
  "source": "YouTube",
  "filter": {
    "title_contains": "Career Corner"
  },
  "total_videos": 1,
  "videos": [
    {
      "video_id": "abc123",
      "title": "Career Corner: How to Build Your Resume",
      "description": "In this episode...",
      "video_url": "https://www.youtube.com/watch?v=abc123",
      "thumbnail_url": "https://i.ytimg.com/vi/abc123/maxresdefault.jpg",
      "published_at": "2026-01-01T00:00:00Z",
      "duration": "PT5M30S",
      "channel_title": "Your Channel Name",
      "privacy_status": "public",
      "playlists": [
        {
          "playlist_id": "playlist123",
          "playlist_title": "Career Corner"
        }
      ],
      "filter_match": "Career Corner",
      "transcript_available": true,
      "transcript_type": "manual",
      "transcript_language": "English",
      "transcript_language_code": "en",
      "transcript": "Full transcript text here...",
      "transcript_segments": []
    }
  ]
}
```

## GitHub Actions automation

This repo includes a GitHub Actions workflow at:

```text
.github/workflows/update-career-corner.yml
```

It can refresh the JSON every Monday or whenever you manually run it from the Actions tab.

In GitHub, add these repo secrets:

```text
YOUTUBE_API_KEY
YOUTUBE_CHANNEL_ID
CAREER_CORNER_PLAYLIST_ID
```

`CAREER_CORNER_PLAYLIST_ID` can be blank if you want it to scan all playlists.

## GitHub Pages (view JSON in the browser)

This repo includes a small static site at the repository root:

```text
index.html
```

It loads `career_corner_videos.json` from the same branch and shows the formatted JSON string on the page. The raw JSON remains available at its own URL for bots and tools.

To publish it with [GitHub Pages](https://docs.github.com/en/pages):

1. In the repository on GitHub, open **Settings** → **Pages**.
2. Under **Build and deployment**, set **Source** to **Deploy from a branch**.
3. Choose your default branch (for example **main**) and folder **/** (root), then save.

After the first deployment, the viewer is available at:

```text
https://<your-username>.github.io/<repository-name>/
```

The raw feed URL is:

```text
https://<your-username>.github.io/<repository-name>/career_corner_videos.json
```

The empty `.nojekyll` file disables Jekyll so all static assets (including the JSON file) are served as-is.

## How your bot can use it

Your bot should ingest this file:

```text
career_corner_videos.json
```

The main field your bot should learn from is:

```json
"transcript": "..."
```

But it should also store:

```json
"title"
"description"
"video_url"
"thumbnail_url"
"playlists"
```

That way, when the bot answers a student's question, it can point users back to the exact Career Corner video.

Example bot response:

> We covered this in Career Corner: Resume Tips. You can watch the video here: https://www.youtube.com/watch?v=abc123

## Important note about transcripts

Transcripts will only be included when they are available for a video. Some videos may have captions disabled, unavailable, or unsupported. Those videos will still appear in the JSON file, but their `transcript_available` value will be `false`.
