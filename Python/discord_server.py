import discord
from discord.ext import commands
import yt_dlp
import os
import random
import requests
import re
from pydub import AudioSegment
from pydub import playback
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
KEY = None

pathFromTitle = lambda x: os.path.join(DATA_SONGS, f"{x}.{SONG_EXTENSION}")

# Set up Discord bot
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

with open(f"{DATA_FOLDER}//key.txt") as file:
    KEY = file.readline()

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

# Play audio (synchronously)
def playAudio(title, volume):
    tape = AudioSegment.from_file(pathFromTitle(title), format=SONG_EXTENSION)
    playback.play(tape + volume)

# Command to add a song
@bot.command(name="add")
async def add_song(ctx, *, title: str):
    if title in SONG_LIST:
        await ctx.send("This song is already in the list.")
        return
    
    results = query(title)[:5]
    if not results:
        await ctx.send("No results found.")
        return

    options = "\n".join([f"{i+1}) {results[i]}" for i in range(len(results))])
    await ctx.send(f"Choose the correct link:\n{options}")
    
    def check(msg):
        return msg.author == ctx.author and msg.content.isdigit()

    try:
        msg = await bot.wait_for("message", check=check, timeout=30)
        idx = int(msg.content) - 1
        if idx < 0 or idx >= len(results):
            await ctx.send("Invalid selection.")
            return

        SONG_LIST[title] = {
            "youtube": results[idx],
            "rating": 0,
            "ratingcount": 0
        }
        download(results[idx], title)
        await ctx.send(f"Added {title} to the song list.")
        save()
    except asyncio.TimeoutError:
        await ctx.send("Timeout: You took too long to respond.")

# Command to play a random song
@bot.command(name="play")
async def play_song(ctx):
    if not SONG_LIST:
        await ctx.send("No songs available.")
        return

    title = random.choice(list(SONG_LIST.keys()))
    await ctx.send(f"Now playing: {title}")

    # Run playAudio in a separate thread to avoid blocking the bot
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, playAudio, title, VOLUME_ADJUSTMENT)

# Command to rate a song
@bot.command(name="rate")
async def rate_song(ctx, title: str, rating: int):
    if title not in SONG_LIST:
        await ctx.send("Song not found.")
        return
    if rating < 0 or rating > 10:
        await ctx.send("Please provide a rating between 0 and 10.")
        return

    SONG_LIST[title]["rating"] += rating
    SONG_LIST[title]["ratingcount"] += 1
    await ctx.send(f"Thanks for rating {title}. New average: {SONG_LIST[title]['rating'] / SONG_LIST[title]['ratingcount']:.2f}/10")
    save()

# Command to display all songs
@bot.command(name="list")
async def list_songs(ctx):
    if not SONG_LIST:
        await ctx.send("No songs available.")
        return
    song_list = "\n".join(
        [f"{title}: {SONG_LIST[title]['rating'] / SONG_LIST[title]['ratingcount']:.2f}/10" if SONG_LIST[title]['ratingcount'] > 0 
         else f"{title}: unrated" for title in SONG_LIST]
    )
    await ctx.send(f"Songs:\n{song_list}")

# Command to redownload all songs
@bot.command(name="redownload")
async def redownload_songs(ctx):
    for filename in os.listdir(DATA_SONGS):
        file_path = os.path.join(DATA_SONGS, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
    for title in SONG_LIST:
        download(SONG_LIST[title]["youtube"], title)
    await ctx.send("All songs redownloaded.")

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

bot.run(f"{KEY}")
