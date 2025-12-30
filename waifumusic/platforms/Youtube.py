import asyncio
import os
import re
import json
import glob
import random
import logging
from typing import Union

import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from youtubesearchpython.__future__ import VideosSearch

from waifumusic.utils.database import is_on_off
from waifumusic.utils.formatters import time_to_seconds

# ================= LOGGER ================= #

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)

LOGGER = logging.getLogger("YouTube")

# ========================================== #

DOWNLOAD_DIR = "downloads"
COOKIES_DIR = "cookies"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ================= COOKIES ================= #

def cookie_txt_file():
    txt_files = glob.glob(os.path.join(COOKIES_DIR, "*.txt"))
    if not txt_files:
        LOGGER.error("No cookies.txt found in cookies folder")
        raise FileNotFoundError("cookies.txt missing")

    chosen = random.choice(txt_files)
    LOGGER.info(f"Using cookies file: {chosen}")
    return chosen

# =========================================== #

async def check_file_size(link):
    try:
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp",
            "--cookies", cookie_txt_file(),
            "-J",
            link,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            LOGGER.error(stderr.decode())
            return None

        info = json.loads(stdout.decode())
        size = sum(f.get("filesize", 0) for f in info.get("formats", []))
        return size

    except Exception as e:
        LOGGER.exception(e)
        return None


async def shell_cmd(cmd):
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out, err = await proc.communicate()
        return out.decode() if out else err.decode()
    except Exception as e:
        LOGGER.exception(e)
        return None

# ================= MAIN CLASS ================= #

class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.listbase = "https://youtube.com/playlist?list="
        self.regex = r"(?:youtube\.com|youtu\.be)"

    async def exists(self, link: str, videoid=False):
        if videoid:
            link = self.base + link
        return bool(re.search(self.regex, link))

    async def url(self, message: Message):
        messages = [message, message.reply_to_message]
        for msg in messages:
            if not msg:
                continue
            if msg.entities:
                for e in msg.entities:
                    if e.type == MessageEntityType.URL:
                        return msg.text[e.offset:e.offset + e.length]
        return None

    async def details(self, link, videoid=False):
        if videoid:
            link = self.base + link
        results = VideosSearch(link, limit=1)
        r = (await results.next())["result"][0]
        return (
            r["title"],
            r["duration"],
            int(time_to_seconds(r["duration"])) if r["duration"] else 0,
            r["thumbnails"][0]["url"].split("?")[0],
            r["id"],
        )

    async def video(self, link, videoid=False):
        if videoid:
            link = self.base + link
        try:
            proc = await asyncio.create_subprocess_exec(
                "yt-dlp",
                "--cookies", cookie_txt_file(),
                "-g",
                "-f",
                "best[height<=720]",
                link,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            out, err = await proc.communicate()
            return (1, out.decode().strip()) if out else (0, err.decode())
        except Exception as e:
            LOGGER.exception(e)
            return 0, str(e)

    async def playlist(self, link, limit, user_id, videoid=False):
        if videoid:
            link = self.listbase + link
        cmd = f"yt-dlp -i --get-id --flat-playlist --cookies {cookie_txt_file()} --playlist-end {limit} {link}"
        data = await shell_cmd(cmd)
        return [x for x in data.split("\n") if x]

    async def download(
        self,
        link,
        mystic,
        video=False,
        videoid=False,
        songaudio=False,
        songvideo=False,
        format_id=None,
        title=None,
    ):
        if videoid:
            link = self.base + link

        loop = asyncio.get_running_loop()

        def audio_dl():
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": f"{DOWNLOAD_DIR}/%(id)s.%(ext)s",
                "cookiefile": cookie_txt_file(),
                "quiet": True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, download=True)
                return ydl.prepare_filename(info)

        def video_dl():
            ydl_opts = {
                "format": "bestvideo[height<=720]+bestaudio/best",
                "outtmpl": f"{DOWNLOAD_DIR}/%(id)s.%(ext)s",
                "cookiefile": cookie_txt_file(),
                "quiet": True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, download=True)
                return ydl.prepare_filename(info)

        if video:
            if await is_on_off(1):
                path = await loop.run_in_executor(None, video_dl)
                return path, True
        path = await loop.run_in_executor(None, audio_dl)
        return path, True

