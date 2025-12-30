import asyncio
import os
import re
import logging
from typing import Union, Tuple

import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from ytmusicapi import YTMusic

from waifumusic.utils.database import is_on_off
from waifumusic.utils.formatters import time_to_seconds

# ───────────────── LOGGER ─────────────────

LOGGER = logging.getLogger("YouTube")
LOGGER.setLevel(logging.INFO)

# ───────────────── CONFIG ─────────────────

BASE_URL = "https://www.youtube.com/watch?v="
PLAYLIST_URL = "https://youtube.com/playlist?list="
YT_REGEX = r"(youtube\.com|youtu\.be)"

COOKIE_FILE = "cookies.txt"
COOKIE_FILE = COOKIE_FILE if os.path.exists(COOKIE_FILE) else None

PROXY = None  # example: "socks5://127.0.0.1:9050"

yt_music = YTMusic()


# ───────────────── HELPERS ─────────────────

async def shell_cmd(cmd: str) -> str:
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    out, err = await proc.communicate()
    return (out or err).decode("utf-8", "ignore")


# ───────────────── YOUTUBE API ─────────────────

class YouTubeAPI:
    def __init__(self):
        self.reg = re.compile(
            r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])"
        )

    # ───────────── URL PARSER ─────────────

    async def extract_url(self, msg: Message) -> Union[str, None]:
        messages = [msg, msg.reply_to_message] if msg.reply_to_message else [msg]

        for m in messages:
            entities = m.entities or m.caption_entities
            text = m.text or m.caption
            if not entities or not text:
                continue

            for e in entities:
                if e.type == MessageEntityType.URL:
                    return text[e.offset:e.offset + e.length]
                if e.type == MessageEntityType.TEXT_LINK:
                    return e.url
        return None


    async def url(self, message):
        return await self.extract_url(message)

    async def exists(self, link: str) -> bool:
        return bool(re.search(YT_REGEX, link))

    # ───────────── METADATA (FAST) ─────────────

    async def details(
        self, link: str, videoid: bool = False
    ) -> Union[Tuple[str, str, int, str, str], None]:

        if videoid:
            link = BASE_URL + link

        link = link.split("&")[0]
        LOGGER.info(f"Fetching details → {link}")

        search = await asyncio.to_thread(
            yt_music.search,
            link,
            filter="songs",
            limit=1
        )

        if not search:
            return None

        r = search[0]
        duration = r.get("duration", "00:00")

        return (
            r["title"],
            duration,
            int(time_to_seconds(duration)),
            r["thumbnails"][-1]["url"].split("?")[0],
            r["videoId"],
        )

    # ───────────── STREAM URL ─────────────

    async def video(self, link: str, videoid: bool = False):
        if videoid:
            link = BASE_URL + link

        LOGGER.info(f"Direct stream → {link}")

        cmd = [
            "yt-dlp",
            "-g",
            "-f",
            "best[height<=720]"
        ]

        if COOKIE_FILE:
            cmd += ["--cookies", COOKIE_FILE]

        if PROXY:
            cmd += ["--proxy", PROXY]

        cmd.append(link)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        out, err = await proc.communicate()

        if out:
            return 1, out.decode().split("\n")[0]

        LOGGER.error(err.decode())
        return 0, err.decode()

    # ───────────── PLAYLIST ─────────────

    async def playlist(self, link: str, limit: int, videoid: bool = False):
        if videoid:
            link = PLAYLIST_URL + link

        cmd = (
            f"yt-dlp -i --flat-playlist --get-id "
            f"{f'--cookies {COOKIE_FILE}' if COOKIE_FILE else ''} "
            f"--playlist-end {limit} {link}"
        )

        data = await shell_cmd(cmd)
        return [i for i in data.split("\n") if i]

    # ───────────── DOWNLOAD ─────────────

    async def download(
        self,
        link: str,
        *,
        video: bool = False,
        songaudio: bool = False,
        format_id: str = None,
        title: str = None,
        videoid: bool = False
    ):
        if videoid:
            link = BASE_URL + link

        loop = asyncio.get_running_loop()

        ydl_opts = {
            "quiet": True,
            "geo_bypass": True,
            "nocheckcertificate": True,
            "outtmpl": "downloads/%(id)s.%(ext)s",
        }

        if COOKIE_FILE:
            ydl_opts["cookiefile"] = COOKIE_FILE
        if PROXY:
            ydl_opts["proxy"] = PROXY

        def audio_dl():
            opts = ydl_opts | {
                "format": "bestaudio",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([link])

        def video_dl():
            opts = ydl_opts | {
                "format": "bestvideo[height<=720]+bestaudio",
                "merge_output_format": "mp4",
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([link])

        try:
            if songaudio:
                await loop.run_in_executor(None, audio_dl)
                return True

            if video:
                if not await is_on_off(1):
                    return await self.video(link)

                await loop.run_in_executor(None, video_dl)
                return True

        except Exception as e:
            LOGGER.exception(f"Download failed → {e}")
            return None

