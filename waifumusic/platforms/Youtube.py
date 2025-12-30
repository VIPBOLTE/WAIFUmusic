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

from PURVIMUSIC.utils.database import is_on_off
from PURVIMUSIC.utils.formatters import time_to_seconds


# ================= LOGGER SETUP ================= #

LOGGER = logging.getLogger("PURVI-YT")
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s | %(levelname)s] %(name)s → %(message)s",
)


# ================= COOKIE HANDLER ================= #

def cookie_txt_file():
    folder = f"{os.getcwd()}/cookies"
    log_file = f"{folder}/logs.csv"

    cookies = glob.glob(os.path.join(folder, "*.txt"))

    if not cookies:
        LOGGER.error("No cookie files found!")
        raise FileNotFoundError("Cookies missing")

    cookie = random.choice(cookies)
    LOGGER.info(f"Using cookie → {cookie}")

    try:
        with open(log_file, "a") as f:
            f.write(f"USED → {cookie}\n")
    except Exception as e:
        LOGGER.warning(f"Cookie log write failed: {e}")

    return f"cookies/{os.path.basename(cookie)}"


# ================= UTILS ================= #

async def shell_cmd(cmd):
    LOGGER.info(f"CMD → {cmd}")
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    out, err = await proc.communicate()

    if err:
        LOGGER.error(err.decode())
        return err.decode()

    return out.decode()


async def check_file_size(link):
    LOGGER.info(f"Checking size → {link}")

    proc = await asyncio.create_subprocess_exec(
        "yt-dlp",
        "--cookies", cookie_txt_file(),
        "-J", link,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    out, err = await proc.communicate()

    if err:
        LOGGER.error(err.decode())
        return None

    data = json.loads(out.decode())
    size = sum(f.get("filesize", 0) for f in data.get("formats", []))

    LOGGER.info(f"Estimated Size → {size / (1024*1024):.2f} MB")
    return size


# ================= YOUTUBE API ================= #

class YouTubeAPI:

    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.listbase = "https://youtube.com/playlist?list="
        self.regex = r"(youtube\.com|youtu\.be)"

    async def exists(self, link, videoid=False):
        if videoid:
            link = self.base + link
        return bool(re.search(self.regex, link))

    async def url(self, message: Message):
        for msg in [message, message.reply_to_message]:
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
        link = link.split("&")[0]

        LOGGER.info(f"Fetching details → {link}")
        r = await VideosSearch(link, limit=1).next()
        data = r["result"][0]

        duration = data["duration"]
        seconds = time_to_seconds(duration) if duration else 0

        return (
            data["title"],
            duration,
            int(seconds),
            data["thumbnails"][0]["url"].split("?")[0],
            data["id"]
        )

    async def video(self, link, videoid=False):
        if videoid:
            link = self.base + link

        LOGGER.info(f"Getting direct stream → {link}")

        proc = await asyncio.create_subprocess_exec(
            "yt-dlp",
            "--cookies", cookie_txt_file(),
            "-g",
            "-f", "best[height<=720]",
            link,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        out, err = await proc.communicate()

        if out:
            return 1, out.decode().split("\n")[0]

        LOGGER.error(err.decode())
        return 0, err.decode()

    async def playlist(self, link, limit, user_id, videoid=False):
        if videoid:
            link = self.listbase + link

        cmd = (
            f"yt-dlp -i --flat-playlist --get-id "
            f"--cookies {cookie_txt_file()} "
            f"--playlist-end {limit} {link}"
        )

        data = await shell_cmd(cmd)
        return [i for i in data.split("\n") if i]

    async def formats(self, link, videoid=False):
        if videoid:
            link = self.base + link

        LOGGER.info("Fetching formats")

        ydl = yt_dlp.YoutubeDL({
            "quiet": True,
            "cookiefile": cookie_txt_file()
        })

        info = ydl.extract_info(link, download=False)
        formats = []

        for f in info["formats"]:
            if "dash" in str(f.get("format", "")).lower():
                continue
            if not f.get("filesize"):
                continue
            formats.append({
                "format": f["format"],
                "filesize": f["filesize"],
                "format_id": f["format_id"],
                "ext": f["ext"],
                "note": f.get("format_note")
            })

        LOGGER.info(f"Formats found → {len(formats)}")
        return formats, link

    async def download(
        self,
        link,
        mystic,
        video=False,
        songaudio=False,
        songvideo=False,
        format_id=None,
        title=None,
        videoid=False
    ):
        if videoid:
            link = self.base + link

        loop = asyncio.get_running_loop()
        LOGGER.info(f"Download start → {link}")

        def audio():
            LOGGER.info("Audio download")
            ydl = yt_dlp.YoutubeDL({
                "format": "bestaudio",
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "cookiefile": cookie_txt_file(),
                "quiet": True,
            })
            ydl.download([link])

        def video_dl():
            LOGGER.info("Video download")
            ydl = yt_dlp.YoutubeDL({
                "format": "bestvideo[height<=720]+bestaudio",
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "cookiefile": cookie_txt_file(),
                "merge_output_format": "mp4",
                "quiet": True,
            })
            ydl.download([link])

        try:
            if songaudio:
                await loop.run_in_executor(None, audio)
                return f"downloads/{title}.mp3", True

            if video:
                if not await is_on_off(1):
                    status, url = await self.video(link)
                    if status:
                        return url, False

                size = await check_file_size(link)
                if size and size > 250 * 1024 * 1024:
                    LOGGER.error("File too large")
                    return None

                await loop.run_in_executor(None, video_dl)
                return "downloads", True

        except Exception as e:
            LOGGER.exception(f"Download failed → {e}")
            return None

