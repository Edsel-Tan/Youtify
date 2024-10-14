import warnings
warnings.filterwarnings("ignore")

import requests
import re
import random
import yt_dlp
import os
import multiprocessing
import time
import sys
import ffmpeg
from pydub import AudioSegment
from pydub import playback

# CONSTANTS
DEFAULT_LINK = "https://www.youtube.com"
SEARCH_LINK = "https://www.youtube.com/results"
DATA_FOLDER = "data"
DATA_TXT = DATA_FOLDER + "\\data.txt"
DATA_SONGS = DATA_FOLDER + "\\songs"
INDENT = "     "
SONG_EXTENSION = "wav"
SONG_LIST = {}
DELIMITER = "%%%"
VOLUME_ADJUSTMENT = -20


pathFromTitle = lambda x: f"{DATA_SONGS}\\{x}.{SONG_EXTENSION}"

def inputl(x):
    s = input(x).lower()
    if s == "m":
        menu()
        return
    return s

def createPlaylist():
    playlist_size = 0
    while True:
        try:
            playlist_size = int(inputl("Enter preferred playlist size \n"))

            if playlist_size <= 0:
                print("Enter a positive integer.", end="")
                continue

            break
        except:
            print("Invalid numeral.", end="")
    
    playlist_size = min(len(SONG_LIST), playlist_size)
    playlist = random.sample(list(SONG_LIST.keys()), playlist_size)

    playlist_played = dict(zip(playlist, [False for i in playlist]))
    
    for title in playlist:
        playlist_played[title] = not play(title)
    
    rating = 0
    while True:
        
        try:
            rating = int(inputl("Input rating\n"))

            if rating < 0 or rating > 10:
                continue
            break
        except:
            print("Rating must be between 0 and 10 (inclusive).", end="")

    for title in playlist:
        if playlist_played[title]:
            temp = SONG_LIST[title]
            temp["rating"] += rating
            temp["ratingcount"] += 1

    save()

def redownload():
    for filename in os.listdir(DATA_SONGS):
        file_path = os.path.join(DATA_SONGS, filename)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Failed to delete {file_path}. Reason: {e}")
            exit()
        
    for title in SONG_LIST:
        download(SONG_LIST[title]["youtube"], title)
    
def verify():
    for title in SONG_LIST:
        if not os.path.isfile(pathFromTitle(title)):
            download(SONG_LIST[title]["youtube"], title)

def playAudio(title, volume):
    print(f"Now playing {title} at volume {volume}")
    tape = AudioSegment.from_file(pathFromTitle(title), format=SONG_EXTENSION)
    playback.play(tape + volume)

def play(title):

    player = multiprocessing.Process(target=playAudio, args=(title,VOLUME_ADJUSTMENT))
    player.start()
    
    interupter = multiprocessing.Process(target=interupt, args=())
    interupter.start()

    while player.is_alive() and interupter.is_alive():
        time.sleep(0.1)

    if interupter.is_alive():
        interupter.terminate()

    if player.is_alive():
        player.terminate()
        return True
    
    return False

def interupt():
    sys.stdin = os.fdopen(0)
    return input("Enter to skip the song. \n")


def download(link, title):
    yt_dl_opt = {
        'format': 'bestaudio',
        'outtmpl': f"{DATA_SONGS}\\{title}",
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav'
        }]
        }
    with yt_dlp.YoutubeDL(yt_dl_opt) as dl:
        dl.download(link)

def query(search):
    results_cache = set()
    results = []
    with requests.get(SEARCH_LINK, params={'search_query': search}) as r:
        for match in re.finditer("/watch\?v=[^\\\\\"]*", r.text):
            if DEFAULT_LINK + match.group(0) not in results_cache:
                results_cache.add(DEFAULT_LINK + match.group(0))
                results.append(DEFAULT_LINK + match.group(0))
    return results


def recommend():
    if len(SONG_LIST) == 0:
        print("No songs currently")
    title = random.choice(list(SONG_LIST.keys()))

    if play(title):
        return
    
    rating = 0
    while True:
        try:
            rating = int(inputl("Input rating\n"))

            if rating < 0 or rating > 10:
                continue
            break
        except:
            print("Rating must be between 0 and 10 (inclusive).", end="")

    temp = SONG_LIST[title]
    temp["rating"] += rating
    temp["ratingcount"] += 1

    save()

def save():
    with open(DATA_TXT, "w") as file:
        for title in SONG_LIST:
            rating, ratingcount, youtubelink = (str(SONG_LIST[title]["rating"]), 
                                                str(SONG_LIST[title]["ratingcount"]), 
                                                SONG_LIST[title]["youtube"])

            file.write(DELIMITER.join([title, rating, ratingcount, youtubelink]))
            file.write("\n")

def load():
    with open(DATA_TXT, "r") as file:
        lines = [line.strip("\n") for line in file.readlines()]
        for i in range(len(lines)):
            try:
                title, rating, ratingcount, youtubelink = lines[i].split(DELIMITER)

                SONG_LIST[title] = {}
                SONG_LIST[title]["rating"] = float(rating)
                SONG_LIST[title]["ratingcount"] = int(ratingcount)
                SONG_LIST[title]["youtube"] = youtubelink
            except:
                print(f"Data file corrupted at line {i}-{i+3}")


def add():
    title = inputl("Input song title\n")

    if title in SONG_LIST:
        print("Title taken.")
        return
    
    results = query(title)[:5]
    for idx in range(len(results)):
        print(f"{idx+1}) {results[idx]}")

    while True:
        try:
            idx = int(inputl("Select correct link \n"))
            if idx < 0 and idx > 5:
                print("Index is between 1 and 5 (inclusive).", end="")
            
            break
        except:
            pass

    SONG_LIST[title] = {}
    SONG_LIST[title]["youtube"] = results[idx-1]
    SONG_LIST[title]["rating"] = 0
    SONG_LIST[title]["ratingcount"] = 0

    download(results[idx-1], title)
    print("Added")

    save()

def display(d):
    items = list(d.keys()) 

    for idx in range(len(items)):
        title = items[idx]
        print((f" {f'{idx+1}) {title}'.upper().ljust(50)} "
             f"{'{:.2f}'.format(d[title]['rating'] / d[title]['ratingcount']) if d[title]['ratingcount'] != 0 else 'unrated'}/10" 
             f" rated {d[title]['ratingcount']} time(s)."
        ))
        # print(f"    Youtube: {d[title]['youtube']}")
    
        

def edit():
    title = inputl("Input song title \n")

    matches = []
    for t in SONG_LIST:
        if title in t:
            matches.append(t)

    if len(matches) == 0:
        print("No matches.")
        return
    
    display(dict(zip(matches, [SONG_LIST[title] for title in matches])))

    idx = 0
    while True:
        try:
            idx = int(inputl("Select correct title \n"))

            if idx < 1 and idx > len(matches):
                print(f"Index must be between 1 and {len(matches)} (inclusive).", end="")
                continue
            break
        except:
            pass

    while True:
        title =  matches[idx-1]
        command = inputl("1) E-edit link \n2) D-delete \n3) R-rename \n4) B-break\n")

        match command:

            case "e":
                youtube_link = inputl("Enter new link \n")
                if "www.youtube.com/watch?v=" not in youtube_link:
                    print("Invalid Link")
                    break
                
                with requests.get(youtube_link) as r:
                    if r.status_code != 200:
                        print("Could not open link")
                        return
                    
                os.remove(pathFromTitle(title))
                download(youtube_link, title)

                SONG_LIST[title]["youtube"] = youtube_link
                save()
                return
            
            case "d":
                del SONG_LIST[title]
                os.remove(pathFromTitle(title))
                save()
                return
            
            case "r":
                new_title  = inputl("Input new name \n")
                if new_title == title:
                    return
                if new_title in SONG_LIST:
                    print("Title taken.")
                    break
                SONG_LIST[new_title] = SONG_LIST[title]
                del SONG_LIST[title]
                os.rename(pathFromTitle(title), pathFromTitle(new_title))
                return
            
            case 'b':
                return

def volume():
    global VOLUME_ADJUSTMENT

    volume = 0
    while True:
        try:
            volume = int(inputl("Enter new volume \n"))
            break
        except:
            print("Enter an integer.", end="")
            pass

    VOLUME_ADJUSTMENT = volume
         

COMMANDS = [
    ("r", "recommend", recommend),
    ("p", "playlist", createPlaylist),
    ("d", "display", lambda: display(SONG_LIST)),
    ("a", "add", add),
    ("e", "edit", edit),
    ("v", "volume", volume),
    ("rdl", "redownload", redownload),
    ("b", "break", sys.exit)
]



def menu():
    while True:
        for idx, command in enumerate(COMMANDS):
            command_prefix, command_name, f = command
            print(f"{idx+1}) {command_prefix.upper()}-{command_name}")

        c = inputl("")

        for command in COMMANDS:
            if command[0] == c:
                command[2]()

            

if __name__ == "__main__":
    if not os.path.isdir(DATA_FOLDER):
        os.mkdir(DATA_FOLDER)
        if not os.path.isdir(DATA_SONGS):
            os.mkdir(DATA_SONGS)
    if not os.path.isfile(DATA_TXT):
        with open(DATA_TXT, "w+") as file:
            pass
    load()
    verify()
    menu()
            
        
