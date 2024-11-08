import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import os
import random
import requests
import re
from pydub import AudioSegment
import asyncio

# CONSTANTS
DEFAULT_LINK = "https://www.youtube.com"
SEARCH_LINK = "https://www.youtube.com/results"
DATA_FOLDER = "data"
DATA_TXT = os.path.join(DATA_FOLDER, "data.txt")
DATA_SONGS = os.path.join(DATA_FOLDER, "songs")
SONG_EXTENSION = "wav"
SONG_LIST = {}
DELIMITER = "%%%"
VOLUME_ADJUSTMENT = -20
YOUR_USER_ID = 391614290467094529

KEY = None
with open(f"{DATA_FOLDER}//key.txt") as file:
    KEY = file.readline()

pathFromTitle = lambda x: os.path.join(DATA_SONGS, f"{x}.{SONG_EXTENSION}")

# Initialize bot
intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents =intents)
tree = discord.app_commands.CommandTree(bot)
##bot = commands.Bot(command_prefix="!", intents=intents)

# Load songs
def load():
    with open(DATA_TXT, "r") as file:
        lines = [line.strip("\n") for line in file.readlines()]
        for line in lines:
            try:
                title, rating, ratingcount, youtubelink = line.split(DELIMITER)
                SONG_LIST[title] = {
                    "rating": float(rating),
                    "ratingcount": int(ratingcount),
                    "youtube": youtubelink
                }
            except:
                print(f"Data file corrupted at line: {line}")

# Save songs
def save():
    with open(DATA_TXT, "w") as file:
        for title in SONG_LIST:
            rating, ratingcount, youtubelink = (
                str(SONG_LIST[title]["rating"]),
                str(SONG_LIST[title]["ratingcount"]),
                SONG_LIST[title]["youtube"]
            )
            file.write(DELIMITER.join([title, rating, ratingcount, youtubelink]) + "\n")

# Download song from YouTube
def download(link, title):
    yt_dl_opt = {
        'format': 'bestaudio',
        'outtmpl': f"{pathFromTitle(title)}",
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': SONG_EXTENSION
        }]
    }
    with yt_dlp.YoutubeDL(yt_dl_opt) as dl:
        dl.download([link])

# Search YouTube for a song
def query(search):
    results_cache = set()
    results = []
    with requests.get(SEARCH_LINK, params={'search_query': search}) as r:
        for match in re.finditer("/watch\?v=[^\\\\\"]*", r.text):
            if DEFAULT_LINK + match.group(0) not in results_cache:
                results_cache.add(DEFAULT_LINK + match.group(0))
                results.append(DEFAULT_LINK + match.group(0))
    return results

# Play audio in voice chat
async def playAudioInVC(vc, title, volume):
    audio_source = discord.FFmpegPCMAudio(pathFromTitle(title), options=f"-filter:a volume={volume}dB")
    vc.play(audio_source)
    while vc.is_playing():
        await asyncio.sleep(1)

# Command to add a song
@tree.command(name="add", description="Add a song to the playlist by searching YouTube.")
async def add_song(interaction: discord.Interaction, title: str):
    if interaction.user.id != YOUR_USER_ID:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    if title in SONG_LIST:
        await interaction.response.send_message("This song is already in the list.")
        return
    
    results = query(title)[:5]
    if not results:
        await interaction.response.send_message("No results found.")
        return

    options = "\n".join([f"{i+1}) {results[i]}" for i in range(len(results))])
    await interaction.response.send_message(f"Choose the correct link:\n{options}")

    def check(msg):
        return msg.author == interaction.user and msg.content.isdigit()

    try:
        msg = await bot.wait_for("message", check=check, timeout=30)
        idx = int(msg.content) - 1
        if idx < 0 or idx >= len(results):
            await interaction.followup.send("Invalid selection.")
            return

        SONG_LIST[title] = {
            "youtube": results[idx],
            "rating": 0,
            "ratingcount": 0
        }
        download(results[idx], title)
        await interaction.followup.send(f"Added {title} to the song list.")
        save()
    except asyncio.TimeoutError:
        await interaction.followup.send("Timeout: You took too long to respond.")

# Command to play a random song in voice chat
@tree.command(name="play", description="Play a random song in voice chat.")
async def play_song(interaction: discord.Interaction):
    if not SONG_LIST:
        await interaction.response.send_message("No songs available.")
        return

    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("You need to be in a voice channel to play music.")
        return

    title = random.choice(list(SONG_LIST.keys()))
    vc = await interaction.user.voice.channel.connect()
    await interaction.response.send_message(f"Now playing: {title}")

    await playAudioInVC(vc, title, VOLUME_ADJUSTMENT)
    await vc.disconnect()

# Command to rate a song
@tree.command(name="rate", description="Rate a song from 0 to 10.")
async def rate_song(interaction: discord.Interaction, title: str, rating: int):
    if title not in SONG_LIST:
        await interaction.response.send_message("Song not found.")
        return
    if rating < 0 or rating > 10:
        await interaction.response.send_message("Please provide a rating between 0 and 10.")
        return

    SONG_LIST[title]["rating"] += rating
    SONG_LIST[title]["ratingcount"] += 1
    await interaction.response.send_message(f"Thanks for rating {title}. New average: {SONG_LIST[title]['rating'] / SONG_LIST[title]['ratingcount']:.2f}/10")
    save()

# Command to display all songs
@tree.command(name="list", description="List all songs with their ratings.")
async def list_songs(interaction: discord.Interaction):
    if not SONG_LIST:
        await interaction.response.send_message("No songs available.")
        return
    song_list = "\n".join(
        [f"{title}: {SONG_LIST[title]['rating'] / SONG_LIST[title]['ratingcount']:.2f}/10" if SONG_LIST[title]['ratingcount'] > 0 
         else f"{title}: unrated" for title in SONG_LIST]
    )
    await interaction.response.send_message(f"Songs:\n{song_list}")

# Command to redownload all songs
@tree.command(name="redownload", description="Redownload all songs.")
async def redownload_songs(interaction: discord.Interaction):
    if interaction.user.id != YOUR_USER_ID:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return
    for filename in os.listdir(DATA_SONGS):
        file_path = os.path.join(DATA_SONGS, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
    for title in SONG_LIST:
        download(SONG_LIST[title]["youtube"], title)
    await interaction.response.send_message("All songs redownloaded.")

# Run the bot
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    load()
    if not os.path.isdir(DATA_FOLDER):
        os.mkdir(DATA_FOLDER)
    if not os.path.isdir(DATA_SONGS):
        os.mkdir(DATA_SONGS)
    save()
    await tree.sync()  # Sync all slash commands with Discord

bot.run(f"{KEY}")
