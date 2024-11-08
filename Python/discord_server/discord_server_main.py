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
DATA_HISTORY = os.path.join(DATA_FOLDER, "history.txt")
DATA_TMP = os.path.join(DATA_FOLDER, "tmp")
SONG_EXTENSION = "wav"
SONG_LIST = {}
SONG_LINKS = set()
SONG_HISTORY = {}
SONGS = []
ALIASES = {}
DELIMITER = "\t"
VOLUME_ADJUSTMENT = -20
YES = "✅"
NO = "❎"
PLAYING_QUEUE = {}
RANDOM_MIN = 0
RANDOM_MAX = 1000000000


KEY = None
USER_ID = set()
ADMIN = None


class PlayingQueue:
    guild: int
    vc: discord.VoiceClient
    playingQueue: list[tuple[str, str, bool]]
    playing: bool
    skip: bool

    def __init__(self, guild_id: int, vc: discord.VoiceClient):
        self.guild = guild_id
        self.vc = vc
        self.playingQueue = []
        self.playing = False
        self.skip = False


# Hints
PLAYING_QUEUE : dict[int, PlayingQueue]



        
pathWithExtension = lambda x: f"{x}.{SONG_EXTENSION}"
pathFromSingerTitle = lambda singer, title: os.path.join(DATA_SONGS, f"{singer}-{title}")
pathFromLinkTmp = lambda x: os.path.join(DATA_TMP, f"{x}")

# Initialize bot
intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents =intents)
tree = discord.app_commands.CommandTree(bot)

"""
HELPER FUNCTIONS
"""

def associated(string1: str, string2: str) -> bool:
    string1_parts = string1.split()
    string2_parts = string2.split()
    for part in string1_parts:
        if part in string2:
            return True
    for part in string2_parts:
        if part in string1:
            return True
    return False

# Load songs
def load() -> None:
    global SONG_HISTORY, SONG_LIST, SONGS
    with open(DATA_TXT, "r") as file:
        lines = [line.strip("\n") for line in file.readlines()]
        for line in lines:
            try:
                singer, title, rating, ratingcount, youtubelink = line.split(DELIMITER)
                if singer in SONG_LIST:
                    SONG_LIST[singer][title] = {
                        "rating": float(rating),
                        "ratingcount": int(ratingcount),
                        "youtube": youtubelink,
                    }
                else:
                    SONG_LIST[singer] = {
                        title: {
                            "rating": float(rating),
                            "ratingcount": int(ratingcount),
                            "youtube": youtubelink,
                        }
                    }
                SONGS.append((singer, title))
            except:
                print(f"Data file corrupted at line: {line}")
                SONGS = {}
                SONG_LIST = []

    with open(DATA_HISTORY, "r") as file:
        lines  = [line.strip("\n") for line in file]
        for line in lines:
            try:
                link, count = line.split(DELIMITER)
                count = int(count.strip())
                SONG_HISTORY[link] = count
            except:
                print(f"Data history file corrupted at line: {line}")
                SONG_HISTORY = {}

# Save songs
def save() -> None:
    with open(DATA_TXT, "w") as file:
        for singer in SONG_LIST:
            for title in SONG_LIST[singer]:
                rating, ratingcount, youtubelink = (
                    str(SONG_LIST[singer][title]["rating"]),
                    str(SONG_LIST[singer][title]["ratingcount"]),
                    SONG_LIST[singer][title]["youtube"]
                )
                file.write(DELIMITER.join([singer, title, rating, ratingcount, youtubelink]) + "\n")

# Update histroy
def save_history() -> None:
    with open(DATA_HISTORY, "w") as file:
        for link in SONG_HISTORY:
            file.write(DELIMITER.join([link, str(SONG_HISTORY[link])]) + "\n")


# Download song from YouTube
def download(link: str, path: str) -> None:
    yt_dl_opt = {
        'format': 'bestaudio',
        'outtmpl': f"{path}",
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': SONG_EXTENSION
        }]
    }
    with yt_dlp.YoutubeDL(yt_dl_opt) as dl:
        dl.download([link])


# Download song from YouTube
def downloadTemp(link: str, path: str) -> None:
    yt_dl_opt = {
        'format': 'bestaudio',
        'outtmpl': f"{path}",
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': SONG_EXTENSION
        }]
    }
    with yt_dlp.YoutubeDL(yt_dl_opt) as dl:
        dl.download([link])

# Download song from YouTube
def downloadPernament(link: str, singer: str, title: str) -> None:
    yt_dl_opt = {
        'format': 'bestaudio',
        'outtmpl': f"{pathFromSingerTitle(singer, title)}",
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': SONG_EXTENSION
        }]
    }
    with yt_dlp.YoutubeDL(yt_dl_opt) as dl:
        dl.download([link])

"""
PLAYING QUEUE HELPER FUNCTIONS
"""

# Search YouTube for a song
def query(search: str) -> str:
    results_cache = set()
    results = []
    with requests.get(SEARCH_LINK, params={'search_query': search}) as r:
        for match in re.finditer("/watch\?v=[^\\\\\"]*", r.text):
            if DEFAULT_LINK + match.group(0) not in results_cache:
                results_cache.add(DEFAULT_LINK + match.group(0))
                results.append(DEFAULT_LINK + match.group(0))
    return results


async def enqueue(guild_id: int, vc: discord.VoiceClient, song: tuple[str, str, bool]) -> bool:
    if guild_id not in PLAYING_QUEUE:
        PLAYING_QUEUE[guild_id] = PlayingQueue(guild_id, vc)

    if vc.channel.id != PLAYING_QUEUE[guild_id].vc.channel.id:
        return False
    
    PLAYING_QUEUE[guild_id].playingQueue.append(song)

async def start_playing(guild_id: int):
    PLAYING_QUEUE[guild_id].playing = True
    while len(PLAYING_QUEUE[guild_id].playingQueue) > 0:
        name, path, isTMP = PLAYING_QUEUE[guild_id].playingQueue[0]
        await PLAYING_QUEUE[guild_id].vc.channel.send(f"Now playing: {name}")
        if isTMP:
            download(name, path)
        PLAYING_QUEUE[guild_id].playingQueue.pop(0)
        await playAudioInVC(PLAYING_QUEUE[guild_id].vc, guild_id, pathWithExtension(path))
        if isTMP:
            os.remove(pathWithExtension(path))
        save_history()
    del PLAYING_QUEUE[guild_id]
    await PLAYING_QUEUE[guild_id].vc.disconnect()

# Play audio in voice chat
async def playAudioInVC(vc: discord.VoiceClient, guild_id: int, path: str):
    audio_source = discord.FFmpegPCMAudio(path, options=f"-filter:a volume={VOLUME_ADJUSTMENT}dB")
    vc.play(audio_source)
    while vc.is_playing():
        if PLAYING_QUEUE[guild_id].skip:
            PLAYING_QUEUE[guild_id].skip = False
            vc.stop()
        await asyncio.sleep(1)


"""
AUDIO VC COMMANDS
"""


@tree.command(name = "playall", description="Queues all saved songs.")
async def play_all(interaction: discord.Interaction):
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("You need to be in a voice channel to play music.")
        return
             
    if interaction.guild.id in PLAYING_QUEUE and interaction.user.voice.channel.id != PLAYING_QUEUE[interaction.guild.id].vc.channel.id:
        await interaction.response.send_message("Already playing in another voice channel.")
        return
    
    await interaction.response.send_message("Queueing all songs...")
    for singer in SONG_LIST:
        for title in SONG_LIST[singer]:
            await enqueue(interaction.guild.id, interaction.user.voice.channel, 
                          (f"{singer}-{title}", 
                           pathFromSingerTitle(singer, title), 
                           False))
    
    if not PLAYING_QUEUE[interaction.guild.id].playing:
        await start_playing(interaction.guild.id)
    


@tree.command(name = "clear", description="Clears the queue.")
async def clear(interaction: discord.Interaction):
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("You need to be in a voice channel to clear!")
        return
    
    if interaction.user.guild.id not in PLAYING_QUEUE:
        await interaction.response.send_message("No songs playing!")
        return
    
    if interaction.user.voice.channel.id != PLAYING_QUEUE[interaction.guild.id].vc.channel.id:
        await interaction.response.send_message("Must be in the same voice channel to clear!")
        return

    PLAYING_QUEUE[interaction.user.guild.id].playingQueue = []
    await interaction.response.send_message("Cleared.")

@tree.command(name = "skip", description="Skips the current song.")
async def skip(interaction: discord.Interaction):
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("You need to be in a voice channel to skip!")
        return
    
    if interaction.user.guild.id not in PLAYING_QUEUE:
        await interaction.response.send_message("No songs playing!")
        return
    
    if interaction.user.voice.channel.id != PLAYING_QUEUE[interaction.guild.id].vc.channel.id:
        await interaction.response.send_message("Must be in the same voice channel to skip!")
        return

    PLAYING_QUEUE[interaction.user.guild.id].skip = True
    await interaction.response.send_message("Skipped.")

@tree.command(name="playlink", description="Play a youtube link")
async def play_link(interaction: discord.Interaction, link: str):
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("You need to be in a voice channel to play music.")
        return
    
    if "www.youtube.com/watch?v=" not in link:
        await interaction.response.send_message("Invalid link.")
        return
    
    with requests.get(link) as r:
        if r.status_code != 200:
            await interaction.response.send_message("Could not open link.")
            return
        
    key = random.randint(RANDOM_MIN, RANDOM_MAX)
    path = pathFromLinkTmp(key)

    SONG_HISTORY[link] = 1 + SONG_HISTORY[link] if link in SONG_HISTORY else 1

   
    if await enqueue(interaction.guild.id, interaction.user.voice.channel, (link, path, True)):
        await interaction.response.send_message(f"Already playing in another voice channel.")
        return
    
    await interaction.response.send_message(f"Added {link} to queue.")
    if not PLAYING_QUEUE[interaction.guild.id].playing:
        start_playing(interaction.guild.id)

        
# Command to play a random song in voice chat
@tree.command(name="play", description="Play a random song in voice chat.")
async def play_song(interaction: discord.Interaction):
    if not len(SONGS):
        await interaction.response.send_message("No songs available.")
        return

    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("You need to be in a voice channel to play music.")
        return
    
    if interaction.guild.id in PLAYING_QUEUE and interaction.user.voice.channel.id != PLAYING_QUEUE[interaction.guild.id]["vc-id"]:
        await interaction.response.send_message("Already playing in another voice channel!")
        return

    singer, title = random.choice(SONGS)
    await interaction.response.send_message(f"Added {singer} {title} to queue.")
    enqueue(interaction.guild.id, interaction.user.voice.channel, 
            (f"{singer}-{title}", 
            pathFromSingerTitle(singer, title), 
            False))
    
    if not PLAYING_QUEUE[interaction.guild.id].playing:
        start_playing(interaction.guild.id)



"""
ADMIN FUNCTIONS
"""


# Command to add a song
@tree.command(name="add", description="Add a song to the playlist by searching YouTube.")
async def add_song(interaction: discord.Interaction, title: str, singer: str):
    if interaction.user.id not in USER_ID:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return
    
    singer = singer.lstrip().rstrip()
    title = title.lstrip().rstrip()

    if singer in ALIASES:
        await interaction.response.send_message(f"Singer recognized.", ephemeral=True)
    else:
        await interaction.response.send_message(f"Singer not recognized. Searching for aliases", ephemeral=True)
    
    check_marks = [YES, NO]
    if singer not in ALIASES:
        for alias in SONG_LIST:
            if associated(singer, alias):
                message = await interaction.channel.send(f"Did you mean {alias}?")
                for tmp in check_marks:
                    await message.add_reaction(tmp)

                def check(reaction: discord.Reaction, user: discord.User):
                    return user == interaction.user and str(reaction.emoji) in check_marks
                
                try:
                    reaction, user = await bot.wait_for("reaction_add", timeout=10.0, check=check)
                except asyncio.TimeoutError:
                    await interaction.followup.send("Timeout: You took too long to respond.")
                    return

                if str(reaction) == YES:
                    singer = alias
                    ALIASES[singer] = alias
                    break

    if singer not in SONG_LIST:
        SONG_LIST[singer] = {}

    if title in SONG_LIST[singer]:
        await interaction.followup.send("This song is already in the list.")
        return
    
    results = query(f"{singer} {title}")[:5]
    if not results:
        await interaction.followup.send("No results found.")
        return

    options = "\n".join([f"{i+1}) {results[i]}" for i in range(len(results))])
    await interaction.followup.send(f"Choose the correct link:\n{options}")

    def check(msg):
        return msg.author == interaction.user and msg.content.isdigit()

    try:
        msg = await bot.wait_for("message", check=check, timeout=30)
        idx = int(msg.content) - 1
        if idx < 0 or idx >= len(results):
            await interaction.followup.send("Invalid selection.")
            return

        SONG_LIST[singer][title] = {
            "youtube": results[idx],
            "rating": 0,
            "ratingcount": 0
        }
        if results[idx] in SONG_LINKS:
            await interaction.followup.send(f"Song already exists as ")
        downloadPernament(results[idx], singer, title)
        await interaction.followup.send(f"Added {title} to the song list.")
        save()
    except asyncio.TimeoutError:
        await interaction.followup.send("Timeout: You took too long to respond.")


    
@tree.command(name="showtop", description="Show top n most replayed songs")
async def show_top(interaction: discord.Interaction, n: int):
    if interaction.user.id != ADMIN:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    song_history = sorted([(SONG_HISTORY[link], link) for link in SONG_HISTORY], reverse=True)
    await interaction.response.send_message("\n".join([f"{entry[1]} played {entry[0]} times." for entry in song_history[:n]]))
    return

@tree.command(name="playtop", description="Play top n most replayed songs")
async def play_top(interaction: discord.Interaction, n: int):
    if interaction.user.id != ADMIN:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    song_history = sorted([(SONG_HISTORY[link], link) for link in SONG_HISTORY], reverse=True)
    for count, link in song_history[:n]:
        
    


# Command to rate a song
@tree.command(name="rate", description="Rate a song from 0 to 10.")
async def rate_song(interaction: discord.Interaction, singer: str, title: str, rating: int):
    if singer not in SONG_LIST and title not in SONG_LIST[singer]:
        await interaction.response.send_message("Song not found.")
        return
    if rating < 0 or rating > 10:
        await interaction.response.send_message("Please provide a rating between 0 and 10.")
        return

    SONG_LIST[singer][title]["rating"] += rating
    SONG_LIST[title][title]["ratingcount"] += 1
    await interaction.response.send_message(f"Thanks for rating {title}. New average: {SONG_LIST[singer][title]['rating'] / SONG_LIST[singer][title]['ratingcount']:.2f}/10")
    save()

# Command to display all songs
@tree.command(name="list", description="List all songs with their ratings.")
async def list_songs(interaction: discord.Interaction):
    if not SONG_LIST:
        await interaction.response.send_message("No songs available.")
        return
    song_list = "\n".join([
        "\n".join(
            [f"{singer}-{title}: {SONG_LIST[singer][title]['rating'] / SONG_LIST[singer][title]['ratingcount']:.2f}/10" if SONG_LIST[singer][title]['ratingcount'] > 0 
            else f"{title}: unrated" for title in SONG_LIST[singer]]) 
        for singer in SONG_LIST])
    await interaction.response.send_message(f"Songs:\n{song_list}")

# Command to redownload all songs
@tree.command(name="redownload", description="Redownload all songs.")
async def redownload_songs(interaction: discord.Interaction):
    if interaction.user.id != ADMIN:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return
    for filename in os.listdir(DATA_SONGS):
        file_path = os.path.join(DATA_SONGS, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
    for singer in SONG_LIST:
        for title in SONG_LIST[singer]:
            downloadPernament(SONG_LIST[singer][title]["youtube"], singer, title)
    await interaction.response.send_message("All songs redownloaded.")

# Run the bot
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await tree.sync()  # Sync all slash commands with Discord


if not os.path.isdir(DATA_FOLDER):
    os.mkdir(DATA_FOLDER)
    if not os.path.isdir(DATA_SONGS):
        os.mkdir(DATA_SONGS)
if not os.path.isfile(DATA_TXT):
    with open(DATA_TXT, "w+") as file:
        pass
if not os.path.isfile(DATA_HISTORY):
    with open(DATA_HISTORY, "w+") as file:
        pass


with open(f"{DATA_FOLDER}//key.txt") as file:
    KEY = file.readline()
with open(f"{DATA_FOLDER}//whitelist.txt") as file:
    ADMIN = int(file.readline())
    USER_ID.add(ADMIN)
    for line in file:
        try:
            USER_ID.add(int(line.rstrip()))
        except:
            print(f"Data file corrupted at line: {line}")
for filename in os.listdir(DATA_TMP):
    file_path = os.path.join(DATA_TMP, filename)
    if os.path.isfile(file_path):
        os.remove(file_path)



load()


bot.run(f"{KEY}")
