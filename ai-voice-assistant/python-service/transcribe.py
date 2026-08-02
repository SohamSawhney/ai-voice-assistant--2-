"""
transcribe.py
-------------
Handles turning a YouTube URL (or any video/audio URL, or local file) into
plain text.

Strategy:
1. Try YouTube's own captions via youtube-transcript-api (fast, free, no
   download needed).
2. If that fails (no captions, not a YouTube URL, private video, etc.),
   fall back to downloading the audio with yt-dlp and transcribing it
   locally with OpenAI's Whisper model.
"""

import os
import re
import tempfile
from typing import Optional

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)


def extract_youtube_id(url: str) -> Optional[str]:
    """Pull the 11-char video id out of any common YouTube URL shape."""
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
        r"youtu\.be\/([0-9A-Za-z_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def get_youtube_captions(url: str) -> Optional[str]:
    """Try to pull existing captions/subtitles straight from YouTube."""
    video_id = extract_youtube_id(url)
    if not video_id:
        return None

    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(
            video_id, languages=["en", "en-US", "en-GB", "hi"]
        )
        text = " ".join(chunk["text"] for chunk in transcript_list)
        return text.strip()
    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable):
        return None
    except Exception:
        return None


def download_audio(url: str, out_dir: str) -> str:
    """Download best-audio track with yt-dlp, return path to the file."""
    import yt_dlp

    out_path = os.path.join(out_dir, "audio.%(ext)s")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": out_path,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "quiet": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    # After conversion, the file will end in .mp3
    for f in os.listdir(out_dir):
        if f.startswith("audio") and f.endswith(".mp3"):
            return os.path.join(out_dir, f)
    raise FileNotFoundError("Audio download/conversion failed")


def whisper_transcribe(audio_path: str, model_size: str = "base") -> str:
    """Transcribe a local audio file with Whisper."""
    import whisper

    model = whisper.load_model(model_size)
    result = model.transcribe(audio_path)
    return result["text"].strip()


def transcribe_video(url_or_path: str, is_local_file: bool = False) -> str:
    """
    Main entry point.
    - If it's a YouTube URL, first try captions (fast path).
    - Otherwise (or if captions fail), download + Whisper it.
    """
    if not is_local_file:
        captions = get_youtube_captions(url_or_path)
        if captions:
            return captions

    with tempfile.TemporaryDirectory() as tmp_dir:
        if is_local_file:
            audio_path = url_or_path
        else:
            audio_path = download_audio(url_or_path, tmp_dir)
        text = whisper_transcribe(audio_path)
        return text
