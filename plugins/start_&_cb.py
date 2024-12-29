import random
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ForceReply, CallbackQuery, Message, InputMediaPhoto

from helper.database import madflixbotz
from config import Config, Txt 



def decode_file_link(encoded_data: str) -> tuple:
    """Decode the Base64 string back into channel_id and message_id."""
    data = base64.urlsafe_b64decode(encoded_data.encode()).decode()
    return tuple(map(int, data.split(":")))

@Client.on_message(filters.private & filters.command("start"))
async def start(client: Client, message: Message):
    """Start command handler."""
    if len(message.command) > 1:
        # Handle the start parameter (decoded Base64)
        encoded_data = message.command[1]
        try:
            channel_id, message_id = decode_file_link(encoded_data)

            # Fetch the file from the file store channel
            file_msg = await client.get_messages(channel_id, message_id)
            await file_msg.copy(message.chat.id)  # Send the file to the user
        except Exception as e:
            await message.reply_text(f"Invalid link or error: {str(e)}")
    else:
        await message.reply_text(
            "Hello! Send me a poster and files to create sharable posts with quality buttons."
        )





# Jishu Developer 
# Don't Remove Credit 🥺
# Telegram Channel @Madflix_Bots
# Developer @JishuDeveloper
