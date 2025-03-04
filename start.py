import asyncio
import random
from telegram import Update
from telegram.ext import ApplicationBuilder, CallbackContext, CommandHandler, MessageHandler, filters
from pymongo import MongoClient

from shivu import collection, user_collection, shivuu, application

# Global variables
current_character = {}
all_characters = []
streaks = {}

ALLOWED_USER_ID = 6806897901
ALLOWED_CHAT_ID = -1002453608705

# Preload characters from the database
async def preload_characters(context: CallbackContext) -> None:
    global all_characters
    try:
        all_characters = await collection.find({}).to_list(length=None)
        if all_characters:
            print(f"Preloaded {len(all_characters)} characters from the database.")
        else:
            print("No characters found in the database.")
    except Exception as e:
        print(f"Error preloading characters: {e}")

# Add coins to user
async def add_coins(user_id: int, amount: int) -> None:
    try:
        if amount <= 0:
            print("Attempted to add non-positive amount of coins.")
            return
        await user_collection.update_one(
            {"id": user_id},
            {"$inc": {"coins": amount}},
            upsert=True
        )
    except Exception as e:
        print(f"Error adding coins: {e}")

# Handle /nguess command
async def nguess(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id

    if chat_id != ALLOWED_CHAT_ID:
        return

    if chat_id in current_character:
        await context.bot.send_message(chat_id, "A guess is already in progress.")
        return

    if not all_characters:
        await context.bot.send_message(chat_id, "No characters available.")
        return

    character = random.choice(all_characters)
    current_character[chat_id] = {
        "character": character,
        "guessed": False,
    }

    # Schedule timeout
    task = asyncio.create_task(send_timeout_message(chat_id, character['name'], 15))
    current_character[chat_id]["timeout"] = task

    await context.bot.send_photo(chat_id=chat_id, photo=character['img_url'], caption="✨🌟 Who is this Mysterious Character?? 🧐🌟✨")

# Handle user guesses
async def handle_guess(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    guess = update.message.text.strip().lower()

    if chat_id in current_character:
        data = current_character[chat_id]
        character = data["character"]
        character_name = character['name'].strip().lower()

        if not data["guessed"] and guess in character_name.split():
            await add_coins(user_id, 20)

            if chat_id not in streaks:
                streaks[chat_id] = {"streak": 1, "misses": 0}
            else:
                streaks[chat_id]["streak"] += 1
                streaks[chat_id]["misses"] = 0

            streak = streaks[chat_id]["streak"]
            await update.message.reply_text(f"🎉 Correct! You've earned 20 coins! Your current streak is {streak}! 🎉")

            # Cancel timeout task
            data["timeout"].cancel()
            data["guessed"] = True

            # Reward streaks
            reward_map = {30: 1000, 50: 1500, 100: 2000}
            if streak in reward_map:
                await add_coins(user_id, reward_map[streak])
                await update.message.reply_text(f"🎉 {streak}-streak! Earned {reward_map[streak]} coins! 🎉")

                if streak == 100:
                    streaks[chat_id]["streak"] = 0  # Reset at 100

        del current_character[chat_id]

# Timeout function
async def send_timeout_message(chat_id: int, character_name: str, timeout: int) -> None:
    await asyncio.sleep(timeout)
    
    if chat_id in current_character and not current_character[chat_id]["guessed"]:
        await application.bot.send_message(chat_id, f"⏳ Time's up! The character was **{character_name}**.")
        del current_character[chat_id]

# Command and message handlers
application.add_handler(CommandHandler('nguess', nguess))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_guess))
