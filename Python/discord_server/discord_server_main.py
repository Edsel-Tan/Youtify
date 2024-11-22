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

from consts import *
from structs import *
import database

# GLOBALS
SONG_LINKS = set()
SONG_HISTORY = {}
SONGS = []
SONG_NAMES = {}
ALIASES = {}
VOLUME_ADJUSTMENT = -20
PLAYING_QUEUE = {}

# ADMINS
KEY = None
USER_ID = set()
ADMIN = None

# Hints
PLAYING_QUEUE: dict[int, PlayingQueue]
SONG_NAMES: dict[str, Song]
SONG_LINKS: set[str]
SONG_HISTORY: dict[str, int]
SONGS: list[Song]
ALIASES: dict[str, str]
VOLUME_ADJUSTMENT: int


# Initialize bot
intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents =intents)
tree = discord.app_commands.CommandTree(bot)

"""
HELPER FUNCTIONS
"""

def associated(string1: str, string2: str) -> bool:
    string1_parts = string1.lower().split()
    string2_parts = string2.lower().split()
    for part in string1_parts:
        if part in string2:
            return True
    for part in string2_parts:
        if part in string1:
            return True
    return False

# Load songs
def load():
    database.init_aliases(ALIASES)
    database.init_songs(SONGS, SONG_LINKS, SONG_NAMES)
    database.init_songs_history(SONG_HISTORY)


# Download song
def download(song: Song):
    yt_dl_opt = {
        'format': 'bestaudio',
        'outtmpl': f"{song.path()}",
        'noplaylist': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': SONG_EXTENSION
        }]
    }
    with yt_dlp.YoutubeDL(yt_dl_opt) as dl:
        dl.download([song.link])

def get_duration(link: str):
    yt_dl_opt = {
        'quiet': True,
    }

    with yt_dlp.YoutubeDL(yt_dl_opt) as dl:
        metadict = dl.extract_info(link, download=False)
        return metadict['duration']
    
    return MAX_DURATION

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


def enqueue(guild_id: int, vc: discord.VoiceState, song: Song) -> bool:
    if guild_id not in PLAYING_QUEUE:
        PLAYING_QUEUE[guild_id] = PlayingQueue(guild_id, vc)

    if vc.channel.id != PLAYING_QUEUE[guild_id].vc.channel.id:
        return False
    
    PLAYING_QUEUE[guild_id].playingQueue.append(song)

async def start_playing(guild_id: int):
    PLAYING_QUEUE[guild_id].playing = True
    PLAYING_QUEUE[guild_id].vc_client = await PLAYING_QUEUE[guild_id].vc.channel.connect()
    while len(PLAYING_QUEUE[guild_id].playingQueue) > 0:
        song = PLAYING_QUEUE[guild_id].playingQueue[0]
        if PLAYING_QUEUE[guild_id].vc.channel:
            await PLAYING_QUEUE[guild_id].vc.channel.send(f"Now playing: {song.name()}")
        else:
            del PLAYING_QUEUE[guild_id]
            return
        if song.temp:
            download(song)
        PLAYING_QUEUE[guild_id].playingQueue.pop(0)
        await playAudioInVC(PLAYING_QUEUE[guild_id].vc_client, guild_id, song.pathWithExtension())
        if song.temp:
            os.remove(song.pathWithExtension())
    await PLAYING_QUEUE[guild_id].vc_client.disconnect()
    del PLAYING_QUEUE[guild_id]

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

@tree.command(name = "playlist", description="Plays all songs in a Youtube Playlist.")
async def play_playlist(interaction: discord.Interaction, link: str):
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
        
    await interaction.response.send_message("Queueing all songs...")
    


@tree.command(name = "playall", description="Queues all saved songs.")
async def play_all(interaction: discord.Interaction):
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("You need to be in a voice channel to play music.")
        return
             
    if interaction.guild.id in PLAYING_QUEUE and interaction.user.voice.channel.id != PLAYING_QUEUE[interaction.guild.id].vc.channel.id:
        await interaction.response.send_message("Already playing in another voice channel.")
        return
    
    await interaction.response.send_message("Queueing all songs...")
    for song in SONGS:
        enqueue(interaction.guild.id, interaction.user.voice, song)
    
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
        
    if get_duration(link) > MAX_DURATION:
        await interaction.response.send_message("Duration exceeds maximum allowed limit (10 minutes).")
        return
        
    key = random.randint(RANDOM_MIN, RANDOM_MAX)
    song = Song("", str(key), link, 0, 0, True)

    if link in SONG_HISTORY:
        SONG_HISTORY[link] += 1
        database.update_song_history((link, SONG_HISTORY[link]))
    else:
        SONG_HISTORY[link] = 1
        database.add_song_history((link, SONG_HISTORY[link]))

    if interaction.guild.id in PLAYING_QUEUE and interaction.user.voice.channel.id != PLAYING_QUEUE[interaction.guild.id].vc.channel.id:
        await interaction.response.send_message("Already playing in another voice channel!")
        return

    enqueue(interaction.guild.id, interaction.user.voice, song)
    await interaction.response.send_message(f"Added {link} to queue.")
    if not PLAYING_QUEUE[interaction.guild.id].playing:
        await start_playing(interaction.guild.id)

        
# Command to play a random song in voice chat
@tree.command(name="play", description="Play a random song in voice chat.")
async def play_song(interaction: discord.Interaction):
    if not len(SONGS):
        await interaction.response.send_message("No songs available.")
        return

    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("You need to be in a voice channel to play music.")
        return
    
    if interaction.guild.id in PLAYING_QUEUE and interaction.user.voice.channel.id != PLAYING_QUEUE[interaction.guild.id].vc.channel.id:
        await interaction.response.send_message("Already playing in another voice channel!")
        return

    song = random.choice(SONGS)
    await interaction.response.send_message(f"Added {song.name()} to queue.")
    enqueue(interaction.guild.id, interaction.user.voice, song)
    
    if not PLAYING_QUEUE[interaction.guild.id].playing:
        await start_playing(interaction.guild.id)



"""
ADMIN FUNCTIONS
"""

@tree.command(name='editsinger', description="Edits a saved song.")
async def edit_singer(interaction: discord.Interaction, old_singer: str, new_singer: str):
    if interaction.user.id not in USER_ID:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    old_singer = old_singer.lstrip().rstrip()
    new_singer = new_singer.lstrip().rstrip()

    if old_singer not in ALIASES or ALIASES[old_singer] != old_singer:
        print(ALIASES)
        await interaction.response.send_message("Singer not recognized.", ephemeral=True)
        return
    
    if new_singer in ALIASES and ALIASES[new_singer] == new_singer:
        await interaction.response.send_message(f"There is already a singer by the name of {new_singer}", ephemeral=True)
        return

    for alias in ALIASES:
        if ALIASES[alias] == old_singer and alias != old_singer:
            ALIASES[alias] = new_singer
            database.edit_alias((alias, old_singer), (alias, new_singer))
        
    del ALIASES[old_singer]
    ALIASES[new_singer] = new_singer
    database.edit_alias((old_singer, old_singer), (new_singer, new_singer))
    
    for song in SONGS:
        if song.singer == old_singer:
            old_song = song.__copy__()
            song.singer = new_singer
            database.edit_song(old_song, song)
            del SONG_NAMES[old_song.name()]
            SONG_NAMES[song.name()] = song

    await interaction.response.send_message("Done.", ephemeral=True)
    return

    

            
    

# Command to add a song
@tree.command(name="add", description="Add a song to the playlist by searching YouTube.")
async def add_song(interaction: discord.Interaction, singer: str, title: str):
    if interaction.user.id not in USER_ID:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return
    
    singer = singer.lstrip().rstrip()
    title = title.lstrip().rstrip()

    if singer in ALIASES:
        singer = ALIASES[singer]
        await interaction.response.send_message(f"Singer recognized.", ephemeral=True)
    else:
        await interaction.response.send_message(f"Singer not recognized. Searching for aliases", ephemeral=True)
    
    check_marks = [YES, NO]
    if singer not in ALIASES:
        for alias in set(ALIASES.values()):
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
                    ALIASES[singer] = alias
                    singer = alias
                    database.add_alias((singer, alias))
                    break
    
    song_name = Song.format(singer, title)

    if song_name in SONG_NAMES:
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
        
        link = results[idx]
        
        if link in SONG_LINKS:
            await interaction.followup.send(f"Song already exists")
            return
        
        song = Song(singer, title, link, 0, 0)
        download(song)
        SONGS.append(song)
        SONG_NAMES[song_name] = song
        SONG_LINKS.add(link)
        database.add_song(song)
        if singer not in ALIASES:
            ALIASES[singer] = singer
            database.add_alias((singer, singer))
        
        await interaction.followup.send(f"Added {song.name()} to the song list.")
        
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

    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("You need to be in a voice channel to play music.")
        return

    if interaction.guild.id in PLAYING_QUEUE and interaction.user.voice.channel.id != PLAYING_QUEUE[interaction.guild.id].vc.channel.id:
        await interaction.response.send_message("Already playing in another voice channel!")
        return

    song_history = sorted([(SONG_HISTORY[link], link) for link in SONG_HISTORY], reverse=True)
    for count, link in song_history[:n]:
        key = random.randint(RANDOM_MIN, RANDOM_MAX)
        enqueue(interaction.guild.id, interaction.user.voice, Song.TEMP_SONG(key, link))

    if not PLAYING_QUEUE[interaction.guild.id].playing:
        await start_playing(interaction.guild.id)


# Command to rate a song
@tree.command(name="rate", description="Rate a song from 0 to 10.")
async def rate_song(interaction: discord.Interaction, singer: str, title: str, rating: int):
    song_name = Song.format(singer, title)

    if song_name not in SONG_NAMES:
        await interaction.response.send_message("Song not found.")
        return
    if rating < 0 or rating > 10:
        await interaction.response.send_message("Please provide a rating between 0 and 10.")
        return
    
    song = SONG_NAMES[song_name]
    song.rating += rating
    song.ratingcount += 1
    database.update_song(song)
    await interaction.response.send_message(f"Thanks for rating {song_name}. New average: {song.rating/song.ratingcount}")
    
    
# Command to display all songs
@tree.command(name="list", description="List all songs with their ratings.")
async def list_songs(interaction: discord.Interaction):
    if not len(SONGS):
        await interaction.response.send_message("No songs available.")
        return
    song_list = "\n".join((str(song) for song in SONGS))
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
    for song in SONGS:
        download(song)
    await interaction.response.send_message("All songs redownloaded.")

@tree.command(name="reconfigure", description="Reconfigure SQL tables. Drops all aliases")
async def reconfigure(interaction: discord.Interaction):
    if interaction.user.id != ADMIN:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return
    
    await interaction.response.send_message("Reconfiguring...", ephemeral=True)

    database.drop_all()
    database.init_aliases(dict())
    database.init_songs(list(), set(), dict())
    database.init_songs_history(dict())
    ALIASES = {}
    for song in SONGS:
        database.add_song(song)
        ALIASES[song.singer] = song.singer
    for alias in ALIASES:
        database.add_alias((alias, ALIASES[alias]))
    for link in SONG_HISTORY:
        database.add_song_history((link, SONG_HISTORY[link]))

    await interaction.followup.send("Done.", ephemeral=True)
    database.DEBUG = False
    return

# Run the bot
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await tree.sync()  # Sync all slash commands with Discord


if not os.path.isdir(DATA_FOLDER):
    os.mkdir(DATA_FOLDER)
if not os.path.isdir(DATA_SONGS):
    os.mkdir(DATA_SONGS)
if not os.path.isdir(DATA_TEMP):
    os.mkdir(DATA_TEMP)
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
for filename in os.listdir(DATA_TEMP):
    file_path = os.path.join(DATA_TEMP, filename)
    if os.path.isfile(file_path):
        os.remove(file_path)



load()


bot.run(f"{KEY}")
