"""Downloads audio from URLs using yt-dlp."""

import os
import pathlib

import yt_dlp


def download_audio(url: str, output_dir: pathlib.Path) -> pathlib.Path:
    """Downloads audio from a URL to a local directory.

    Args:
        url: The URL of the video or audio to download.
        output_dir: Directory where the audio file will be saved.

    Returns:
        Path to the downloaded audio file.
    """
    output_template = str(output_dir / "%(id)s.%(ext)s")
    ydl_opts = {
        "format": "bestaudio",
        "outtmpl": output_template,
        "quiet": False,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "opus",
        }],
    }

    cookies_file = os.environ.get("YTDLP_COOKIES_FILE")
    if cookies_file:
        ydl_opts["cookiefile"] = cookies_file

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    return output_dir / f"{info['id']}.opus"
