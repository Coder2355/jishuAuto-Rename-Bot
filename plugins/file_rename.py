

from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from PIL import Image
from datetime import datetime
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from helper.utils import progress_for_pyrogram, humanbytes, convert
from helper.database import madflixbotz
from config import Config
import os
import time
import re
import base64

# Constants
STORE_CHANNEL = -1002134913785  # Replace with your store channel ID
TARGET_CHANNEL = -1002245327685
POSTER = None
EPISODE_LINKS = {}

renaming_operations = {}  # Track renaming operations


# Utility function
def encode_file_id(file_id):
    return base64.urlsafe_b64encode(file_id.encode()).decode()


# Quality patterns
pattern_quality = re.compile(r'(480p|720p|1080p|4k|2k|HdRip|4kx265|4kX264)', re.IGNORECASE)

# Function to extract quality
def extract_quality(filename):
    match = re.search(pattern_quality, filename)
    return match.group(1) if match else "Unknown"

# Function to extract episode number
def extract_episode_number(filename):
    patterns = [
        r'S(\d+)(?:E|EP)(\d+)',  # S01E02 or S01EP02
        r'S(\d+)\s*(?:E|EP|-\s*EP)(\d+)',  # S01 E02 or S01 - EP02
        r'(?:E|EP)(\d+)',  # Episode number after E or EP
        r'S(\d+)[^\d]*(\d+)'  # S2 09 style
    ]
    for pattern in patterns:
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            return match.group(2)
    return None


@Client.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def auto_rename_files(client, message):
    global POSTER
    user_id = message.from_user.id
    format_template = await madflixbotz.get_format_template(user_id)
    media_preference = await madflixbotz.get_media_preference(user_id)

    if not format_template:
        return await message.reply_text("Please set an auto-rename format using /autorename")

    # Get file details
    if message.document:
        file_id = message.document.file_id
        file_name = message.document.file_name
        media_type = media_preference or "document"
    elif message.video:
        file_id = message.video.file_id
        file_name = f"{message.video.file_name}.mp4"
        media_type = media_preference or "video"
    elif message.audio:
        file_id = message.audio.file_id
        file_name = f"{message.audio.file_name}.mp3"
        media_type = media_preference or "audio"
    else:
        return await message.reply_text("Unsupported file type")

    # Prevent duplicate renaming
    if file_id in renaming_operations:
        elapsed_time = (datetime.now() - renaming_operations[file_id]).seconds
        if elapsed_time < 10:
            return

    renaming_operations[file_id] = datetime.now()

    try:
        # Extract episode and quality
        episode_number = extract_episode_number(file_name)
        file_quality = extract_quality(file_name)

        if episode_number:
            format_template = format_template.replace("{episode}", str(episode_number))
        if file_quality != "Unknown":
            format_template = format_template.replace("{quality}", file_quality)
        else:
            await message.reply_text("Could not detect quality. Defaulting to 'Unknown'.")

        # Generate new filename
        _, file_extension = os.path.splitext(file_name)
        new_file_name = f"{format_template}{file_extension}"
        file_path = f"downloads/{new_file_name}"

        # Download file
        download_msg = await message.reply_text("Downloading file...")
        path = await client.download_media(
            message=message, 
            file_name=file_path, 
            progress=progress_for_pyrogram, 
            progress_args=("Downloading...", download_msg, time.time())
        )

        # Get metadata
        metadata = extractMetadata(createParser(path))
        duration = metadata.get("duration").seconds if metadata and metadata.has("duration") else 0

        # Upload file
        upload_msg = await download_msg.edit("Uploading file...")
        caption = f"**{new_file_name}**\nSize: {humanbytes(message.document.file_size)}\nDuration: {convert(duration)}"

        # Thumbnail
        c_thumb = await madflixbotz.get_thumbnail(user_id)
        thumb_path = await client.download_media(c_thumb) if c_thumb else None

        # Send file
        sent_message = await client.send_document(
            chat_id=message.chat.id,
            document=file_path,
            thumb=thumb_path,
            caption=caption,
            progress=progress_for_pyrogram,
            progress_args=("Uploading...", upload_msg, time.time())
        )

        # Forward to store channel
        forwarded = await sent_message.forward(STORE_CHANNEL)
        file_id = forwarded.id
        encoded_id = encode_file_id(str(file_id))
        link = f"https://t.me/{STORE_CHANNEL}/{file_id}?id={encoded_id}"
        quality = None
        if "480p" in file_quality:
            quality = "480p"
        elif "720p" in file_quality:
            quality = "720p"
        elif "1080p" in file_quality:
            quality = "1080p"
 
        if not quality:
            await message.reply_text("Please include quality (480p, 720p, 1080p) in the caption.")
            return
        # Create and send episode links
        if episode_number not in EPISODE_LINKS:
            EPISODE_LINKS[episode_number] = {}
        EPISODE_LINKS[episode_number][quality] = link

        buttons = []
        for q in ["480p", "720p", "1080p"]:
            if q in EPISODE_LINKS[episode_number]:
                buttons.append(InlineKeyboardButton(q, url=EPISODE_LINKS[episode_number][q]))


        if len(buttons) > 0:
            await client.send_photo(
                TARGET_CHANNEL,
                photo=POSTER,
                caption=f"Anime: You are MS Servant\nSeason: 01\nEpisode: {episode}\nQuality: {', '.join(EPISODE_LINKS[episode].keys())}\nLanguage: Tamil",
                reply_markup=InlineKeyboardMarkup([buttons]),
           )

        await message.reply_text("Episode posted successfully ✅")


        await message.reply_text("File renamed and uploaded successfully!")

    except Exception as e:
        await message.reply_text(f"Error: {e}")
    finally:
        # Clean up
        del renaming_operations[file_id]
        if os.path.exists(file_path):
            os.remove(file_path)


@Client.on_message(filters.photo & filters.private)
async def handle_poster(client, message):
    global POSTER
    POSTER = message.photo.file_id
    await message.reply_text("Poster added successfully!")


