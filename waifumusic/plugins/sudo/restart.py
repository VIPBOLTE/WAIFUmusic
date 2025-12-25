import asyncio
import socket
from pyrogram import filters

import config
from waifumusic import app
from waifumusic.misc import HAPP, SUDOERS
from waifumusic.utils.database import (
    get_active_chats,
    remove_active_chat,
    remove_active_video_chat,
)
from waifumusic.utils.decorators.language import language
from waifumusic.utils.pastebin import waifuBin


async def is_heroku():
    """Check if bot is running on Heroku."""
    return "heroku" in socket.getfqdn()


@app.on_message(filters.command(["getlog", "logs", "getlogs"]) & SUDOERS)
@language
async def log_(client, message, _):
    """Send log file."""
    try:
        await message.reply_document(document="log.txt")
    except Exception:
        await message.reply_text(_["server_1"])


@app.on_message(filters.command(["update", "gitpull"]) & SUDOERS)
@language
async def update_(client, message, _):
    """Heroku-safe update handler."""
    if await is_heroku():
        # Heroku cannot run runtime git operations
        return await message.reply_text(
            "⚠️ Heroku detected: runtime git operations are disabled.\n"
            "Please deploy updates via GitHub push or Heroku auto-deploy."
        )

    response = await message.reply_text(_["server_3"])
    # Non-Heroku deployments (VPS) can keep existing git logic if needed
    await response.edit(
        "⚠️ This bot is running outside Heroku. "
        "Auto-update logic can run here if configured."
    )


@app.on_message(filters.command(["restart"]) & SUDOERS)
@language
async def restart_(client, message, _):
    """Heroku-safe restart handler."""
    if await is_heroku():
        # Heroku restart must be done via CLI
        await message.reply_text(
            "⚠️ Heroku detected: use `heroku ps:restart worker` in CLI to restart the bot."
        )
        return

    response = await message.reply_text("ʀᴇsᴛᴀʀᴛɪɴɢ bot...")
    # Non-Heroku: safely notify active chats
    served_chats = await get_active_chats()
    for x in served_chats:
        try:
            await app.send_message(
                chat_id=int(x),
                text=f"{app.mention} is restarting...\n"
                     "You can start playing again after 15-20 seconds."
            )
            await remove_active_chat(x)
            await remove_active_video_chat(x)
        except Exception:
            pass

    await response.edit_text("✅ Bot restart handled safely. "
                             "Non-Heroku restart logic can be added here.")
