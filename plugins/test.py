from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import base64
import logging
from config import Config

logging.basicConfig(level=logging.INFO)
bot = Client("AutoAnimeBot", api_id=Config.API_ID, api_hash=Config.API_HASH, bot_token=Config.BOT_TOKEN)

# Dictionary to store posters by episode number
posters = {}

@bot.on_message(filters.document | filters.video)
async def handle_file(bot, message):
    try:
        # Extract metadata from the message
        file = message.document or message.video
        episode_number = extract_episode_number(file.file_name)  # Extract episode number from file name
        quality = extract_quality(file.file_name)  # Extract quality (e.g., 480p, 720p, 1080p)
        anime_name = "Custom Anime Name"  # Replace this with logic to dynamically extract anime name
        season = "01"  # Replace this with logic to dynamically extract season

        # Download the file
        download_message = await message.reply(f"Downloading {quality}...")
        file_path = await bot.download_media(file, file_name=file.file_name)
        await download_message.edit(f"Downloaded {quality} file.")

        # Upload to file store channel and generate a link
        upload_message = await message.reply(f"Uploading {quality}...")
        file_store_message = await bot.send_document(chat_id=Config.FILE_STORE_CHANNEL, document=file_path)
        file_link = generate_file_link(file_store_message.message_id)
        await upload_message.edit(f"Uploaded {quality} file.")

        # Check if a poster for this episode already exists
        if episode_number in posters:
            # Update the existing poster with the new quality button
            poster_message_id = posters[episode_number]
            poster_message = await bot.get_messages(chat_id=Config.TARGET_CHANNEL, message_ids=poster_message_id)

            # Update buttons to include the new quality
            new_buttons = update_buttons(poster_message.reply_markup.inline_keyboard, quality, file_link)
            await poster_message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(new_buttons))
        else:
            # Create a new poster
            poster = await message.reply_photo(
                photo=get_thumbnail(file),
                caption=(
                    f"**Anime**: {anime_name}\n"
                    f"**Season**: {season}\n"
                    f"**Episode**: {episode_number}\n"
                    f"**Quality**: {quality}"
                ),
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton(f"{quality}", url=file_link)]]
                )
            )
            # Save poster message ID
            posters[episode_number] = poster.message_id

        # Clean up downloaded file
        os.remove(file_path)
    except Exception as e:
        logging.error(f"Error: {e}")
        await message.reply(f"An error occurred: {e}")

def extract_episode_number(file_name):
    # Logic to extract episode number from the file name
    # Example: "Anime_S01E08_480p.mkv" -> "08"
    return file_name.split("E")[1].split("_")[0]

def extract_quality(file_name):
    # Logic to extract quality from the file name
    # Example: "Anime_S01E08_480p.mkv" -> "480p"
    return file_name.split("_")[-1].replace(".mkv", "")

def get_thumbnail(file):
    # Logic to extract or generate a thumbnail from the file
    # Here, you can use the file thumbnail or a default image
    return Config.DEFAULT_THUMBNAIL

def generate_file_link(message_id):
    # Generate a link using the file store bot
    base64_message_id = base64.urlsafe_b64encode(f"get-{message_id}".encode()).decode()
    return f"https://telegram.me/{Config.FILE_STORE_BOT}?start={base64_message_id}"

def update_buttons(existing_buttons, quality, file_link):
    # Add new quality button to the existing buttons
    new_buttons = []
    quality_exists = False

    for button_row in existing_buttons:
        row = []
        for button in button_row:
            if quality in button.text:
                quality_exists = True
                row.append(InlineKeyboardButton(f"{quality}", url=file_link))
            else:
                row.append(button)
        new_buttons.append(row)

    if not quality_exists:
        new_buttons.append([InlineKeyboardButton(f"{quality}", url=file_link)])

    return new_buttons

bot.run()






import base64
from pyrogram import Client
from pyrogram.types import InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton

# Helper function to generate base64 link
def generate_file_link(file_id: str):
    encoded = base64.b64encode(f"get-{file_id}".encode()).decode()
    return f"https://telegram.me/FZXAutoAniBot?start={encoded}"

async def process_file(client: Client, message):
    anime_name = "I'll Become a Villainess Who Goes Down in History"
    season = "01"
    episode = "08"
    qualities = ["480p", "720p", "1080p"]
    target_channel = -100123456789  # Replace with your target channel ID
    file_store_channel = -100987654321  # Replace with your file store channel ID

    # Step 1: Generate Initial Poster
    thumbnail = message.video.thumbs[0].file_id if message.video else None
    caption = (
        f"Anime: {anime_name}\n"
        f"Season: {season}\n"
        f"Episode: {episode}\n"
        "Quality: "
    )
    post = await client.send_photo(
        target_channel,
        thumbnail,
        caption=caption,
    )

    links = []
    for quality in qualities:
        # Step 2: Show progress for downloading
        await post.edit_caption(caption + f"\n\nDownloading {quality}...")
        file = await message.download(file_name=f"{quality}.mp4")

        # Step 3: Add Metadata (Optional)
        # Assume metadata addition here

        # Step 4: Upload to File Store
        await post.edit_caption(caption + f"\n\nUploading {quality}...")
        uploaded_message = await client.send_document(file_store_channel, file)
        file_link = generate_file_link(uploaded_message.id)
        links.append((quality, file_link))

        # Step 5: Update Poster with Link
        buttons = [
            InlineKeyboardButton(text=q, url=link) for q, link in links
        ]
        await post.edit_caption(
            caption + "+".join([q for q, _ in links]),
            reply_markup=InlineKeyboardMarkup([buttons]),
        )

    # Step 6: Final Completion Message
    await client.send_message(target_channel, "All files uploaded successfully ✅")
