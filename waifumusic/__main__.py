import asyncio
import importlib

from pyrogram import idle
from pytgcalls.exceptions import NoActiveGroupCall

import config
from waifumusic import LOGGER, app, userbot
from waifumusic.core.call import waifu
from waifumusic.misc import sudo
from waifumusic.plugins import ALL_MODULES
from waifumusic.utils.database import get_banned_users, get_gbanned
from config import BANNED_USERS, COOKIES_URL
from waifumusic.plugins.sudo.cookies import set_cookies

async def init():
    if (
        not config.STRING1
        and not config.STRING2
        and not config.STRING3
        and not config.STRING4
        and not config.STRING5
    ):
        LOGGER(__name__).error("⚙️ Assistant client variables not defined, exiting...")
        exit()
    await sudo()
    try:
        users = await get_gbanned()
        for user_id in users:
            BANNED_USERS.add(user_id)
        users = await get_banned_users()
        for user_id in users:
            BANNED_USERS.add(user_id)
    except:
        pass
    await app.start()
    for all_module in ALL_MODULES:
        importlib.import_module("waifumusic.plugins" + all_module)
    LOGGER("waifumusic.plugins").info("✅ Successfully Imported Modules.")
    await userbot.start()
    await waifu.start()
    try:
        await waifu.stream_call("https://te.legra.ph/file/29f784eb49d230ab62e9e.mp4")
    except NoActiveGroupCall:
        LOGGER("AnonMusic").error(
            "🚫 Please turn on the videochat of your log group\channel. Stopping Bot..."
        )
        exit()
    except:
        pass
    await waifu.decorators()
    LOGGER("AnonMusic").info(
        "\x41\x6e\x6f\x6e\x20\x4d\x75\x73\x69\x63\x20\x53\x74\x61\x72\x74\x65\x64\x20\x53\x75\x63\x63\x65\x73\x73\x66\x75\x6c\x6c\x79\x2e\x0a\x0a\x44\x6f\x6e\x27\x74\x20\x66\x6f\x72\x67\x65\x74\x20\x74\x6f\x20\x76\x69\x73\x69\x74\x20\x40\x56\x69\x62\x65\x42\x6f\x74\x73\x20\x3a\x20\x47\x65\x74\x20\x46\x72\x65\x65\x20\x59\x6f\x75\x54\x75\x62\x65\x20\x41\x70\x69\x20\x3a\x20\x40\x4b\x65\x79\x4d\x61\x6b\x65\x72\x52\x6f\x42\x6f\x74"
    )
    
    res = await set_cookies(COOKIES_URL)
    LOGGER("AnonMusic").info(f"{res}")
    await waifu.decorators()
    await idle()
    await app.stop()
    LOGGER("waifuMusic").info("🚫 Stopping AnonMusic Bot...")


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(init())
