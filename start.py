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
        "timeout": asyncio.create_task(send_timeout_message(chat_id, character['name'], 15)) 
    } 
 
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
            streak = streaks.get(chat_id, {}).get("streak", 0) 
            await update.message.reply_text(f"🎉 Correct! You've earned 20 coins! Your current streak is {streak}! 🎉") 
            data["guessed"] = True 
            data["timeout"].cancel() 
 
            if chat_id not in streaks: 
                streaks[chat_id] = {"streak": 1, "misses": 0} 
            else: 
                streaks[chat_id]["streak"] += 1 
                streaks[chat_id]["misses"] = 0 
 
            # Reward streaks 
            if streaks[chat_id]["streak"] == 30: 
                await add_coins(user_id, 1000) 
                await update.message.reply_text(f"🎉 30-streak! Earned 1000 coins! 🎉") 
            elif streaks[chat_id]["streak"] == 50: 
                await add_coins(user_id, 1500) 
                await update.message.reply_text(f"🎉 50-streak! Earned 1500 coins! 🎉") 
            elif streaks[chat_id]["streak"] == 100: 
                await add_coins(user_id, 2000) 
                await update.message.reply_text(f"🎉 100-streak! Earned 2000 coins! 🎉") 
                streaks[chat_id]["streak"] = 0 
 
        del current_character[chat_id] 
 
# Timeout function 
async def send_timeout_message(chat_id: int, character_name: str, timeout: int) -> None: 
    await

asyncio.sleep(timeout) 
    await application.bot.send_message(chat_id, f"Time's up! The character was {character_name}.") 
    del current_character[chat_id] 
 
 
# Main function to start the bot 
def main() -> None:    
 
    # Command and message handlers 
    application.add_handler(CommandHandler('nguess', nguess)) 
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_guess)) 
 
