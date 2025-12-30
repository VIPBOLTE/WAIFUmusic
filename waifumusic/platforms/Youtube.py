import asyncio
import os
import re
from typing import Union

import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from ytmusicapi import YTMusic # Updated library

from waifumusic.utils.database import is_on_off
from waifumusic.utils.formatters import time_to_seconds

# Global instance of YTMusic for faster performance
yt_music = YTMusic()

async def shell_cmd(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, errorz = await proc.communicate()
    if errorz:
        if "unavailable videos are hidden" in (errorz.decode("utf-8")).lower():
            return out.decode("utf-8")
        else:
            return errorz.decode("utf-8")
    return out.decode("utf-8")

# If you don't have cookies.txt, it will still work but might get blocked later
cookies_file = "Spy/cookies.txt"
if not os.path.exists(cookies_file):
    cookies_file = None

class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.status = "https://www.youtube.com/oembed?url="
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    async def exists(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if re.search(self.regex, link):
            return True
        return False

    async def url(self, message_1: Message) -> Union[str, None]:
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        text = ""
        offset = None
        length = None
        for message in messages:
            if offset:
                break
            if message.entities:
                for entity in message.entities:
                    if entity.type == MessageEntityType.URL:
                        text = message.text or message.caption
                        offset, length = entity.offset, entity.length
                        break
            elif message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == MessageEntityType.TEXT_LINK:
                        return entity.url
        if offset in (None,):
            return None
        return text[offset : offset + length]

    # --- Fixed with YTMusic API ---
    async def details(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        
        # Search official songs on YT Music
        search = await asyncio.to_thread(yt_music.search, link, filter="songs", limit=1)
        if not search:
            return None
        
        result = search[0]
        title = result["title"]
        duration_min = result.get("duration", "04:00")
        thumbnail = result["thumbnails"][-1]["url"].split("?")[0]
        vidid = result["videoId"]
        duration_sec = int(time_to_seconds(duration_min))
        
        return title, duration_min, duration_sec, thumbnail, vidid

    async def title(self, link: str, videoid: Union[bool, str] = None):
        res = await self.details(link, videoid)
        return res[0] if res else "Unknown"

    async def duration(self, link: str, videoid: Union[bool, str] = None):
        res = await self.details(link, videoid)
        return res[1] if res else "00:00"

    async def thumbnail(self, link: str, videoid: Union[bool, str] = None):
        res = await self.details(link, videoid)
        return res[3] if res else None

    async def video(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        
        opts = ["yt-dlp", "-g", "-f", "best[height<=?720][width<=?1280]", f"{link}"]
        if cookies_file:
            opts.insert(1, "--cookies")
            opts.insert(2, cookies_file)

        proc = await asyncio.create_subprocess_exec(
            *opts,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if stdout:
            return 1, stdout.decode().split("\n")[0]
        else:
            return 0, stderr.decode()

    async def playlist(self, link, limit, user_id, videoid: Union[bool, str] = None):
        if videoid:
            link = self.listbase + link
        if "&" in link:
            link = link.split("&")[0]
        
        cookie_cmd = f"--cookies {cookies_file}" if cookies_file else ""
        playlist = await shell_cmd(
            f"yt-dlp {cookie_cmd} -i --get-id --flat-playlist --playlist-end {limit} --skip-download {link}"
        )
        try:
            result = [k for k in playlist.split("\n") if k != ""]
        except:
            result = []
        return result

    async def track(self, link: str, videoid: Union[bool, str] = None):
        res = await self.details(link, videoid)
        if not res:
            return None, None
        
        title, duration_min, duration_sec, thumbnail, vidid = res
        track_details = {
            "title": title,
            "link": self.base + vidid,
            "vidid": vidid,
            "duration_min": duration_min,
            "thumb": thumbnail,
        }
        return track_details, vidid

    async def slider(self, link: str, query_type: int, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        
        # Get top 10 results from YT Music
        search = await asyncio.to_thread(yt_music.search, link, filter="songs", limit=10)
        result = search[query_type]
        
        title = result["title"]
        duration_min = result.get("duration", "00:00")
        vidid = result["videoId"]
        thumbnail = result["thumbnails"][-1]["url"].split("?")[0]
        return title, duration_min, thumbnail, vidid

    async def download(
        self, link: str, mystic, video=None, videoid=None, songaudio=None, songvideo=None, format_id=None, title=None
    ) -> str:
        if videoid:
            link = self.base + link
        loop = asyncio.get_running_loop()

        common_opts = {
            "geo_bypass": True,
            "nocheckcertificate": True,
            "quiet": True,
            "no_warnings": True,
        }
        if cookies_file:
            common_opts["cookiefile"] = cookies_file

        def audio_dl():
            ydl_opts = {**common_opts, "format": "bestaudio/best", "outtmpl": "downloads/%(id)s.%(ext)s"}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, False)
                path = os.path.join("downloads", f"{info['id']}.{info['ext']}")
                if not os.path.exists(path):
                    ydl.download([link])
                return path

        def video_dl():
            ydl_opts = {**common_opts, "format": "(bestvideo[height<=?720][width<=?1280][ext=mp4])+(bestaudio[ext=m4a])", "outtmpl": "downloads/%(id)s.%(ext)s"}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, False)
                path = os.path.join("downloads", f"{info['id']}.{info['ext']}")
                if not os.path.exists(path):
                    ydl.download([link])
                return path

        if songvideo:
            fpath = f"downloads/{title}.mp4"
            def sv_dl():
                with yt_dlp.YoutubeDL({**common_opts, "format": f"{format_id}+140", "outtmpl": f"downloads/{title}", "merge_output_format": "mp4"}) as ydl:
                    ydl.download([link])
            await loop.run_in_executor(None, sv_dl)
            return fpath

        elif songaudio:
            fpath = f"downloads/{title}.mp3"
            def sa_dl():
                with yt_dlp.YoutubeDL({**common_opts, "format": format_id, "outtmpl": f"downloads/{title}.%(ext)s", "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}]}) as ydl:
                    ydl.download([link])
            await loop.run_in_executor(None, sa_dl)
            return fpath

        elif video:
            direct = True
            downloaded_file = await loop.run_in_executor(None, video_dl)
        else:
            direct = True
            downloaded_file = await loop.run_in_executor(None, audio_dl)
        
        return downloaded_file, direct
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

