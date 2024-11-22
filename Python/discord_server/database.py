import sqlite3
from consts import *
from structs import *
import shutil
import random
import yt_dlp

DEBUG = False

DATA_DB = os.path.join(DATA_FOLDER, "data.db")
BACKUP_FOLDER = os.path.join(DATA_FOLDER, "backup")
TABLE_SONG_NAME = "songs"
TABLE_SONG_HISTORY_NAME = "songs_history"
TABLE_ALIASES_NAME = "aliases"

TABLE_SONG_COLUMNS = ["singer", "title", "link", "rating", "ratingcount"]
TABLE_SONG_HISTORY_COLUMNS = ["link", "count"]
TABLE_ALIASES_COLUMNS = ["name", "alias"]

TABLE_SONG_COLUMNS_INFO = ["singer TEXT", "title TEXT", "link TEXT", "rating REAL", "ratingcount INT"]
TABLE_SONG_HISTORY_COLUMNS_INFO = ["link TEXT", "count TEXT"]
TABLE_ALIASES_COLUMNS_INFO = ["name TEXT", "alias TEXT"]


def init(table_name: str, col_names_info: str, col_names: str):
    with sqlite3.connect(DATA_DB) as con:
        cur = con.cursor()
        res = cur.execute("SELECT name FROM sqlite_master;")
        if (table_name,) not in res.fetchall():
            print(f"CREATE TABLE {table_name}({col_names})")
            cur.execute(f"CREATE TABLE {table_name}({col_names})")
            return
        
        cur.execute(f"PRAGMA table_info({table_name});")
        res = cur.fetchall()
        if ", ".join([entry[1] for entry in res]) != col_names:
            print("Data corrupted! Wiping tables...")
            cur.execute(f"DROP TABLE {table_name}")



def init_songs(SONGS : list[Song], SONG_LINKS: set[str], SONG_NAMES: dict[str, Song]):
    init(TABLE_SONG_NAME, ", ".join(TABLE_SONG_COLUMNS_INFO), ", ".join(TABLE_SONG_COLUMNS))

    with sqlite3.connect(DATA_DB) as con:
        cur = con.cursor()
        res = cur.execute(f"SELECT * FROM {TABLE_SONG_NAME}")
        for singer, title, link, rating, ratingcount in res.fetchall():
            song = Song(singer, title, link, rating, ratingcount)
            SONGS.append(song)
            SONG_LINKS.add(link)
            SONG_NAMES[song.name()] = song
                

def init_songs_history(SONG_HISTORY : dict[str, int]):
    init(TABLE_SONG_HISTORY_NAME, ", ".join(TABLE_SONG_HISTORY_COLUMNS_INFO), ", ".join(TABLE_SONG_HISTORY_COLUMNS))

    with sqlite3.connect(DATA_DB) as con:
        cur = con.cursor()
        res = cur.execute(f"SELECT * FROM {TABLE_SONG_HISTORY_NAME}")
        for link, count in res.fetchall():
            SONG_HISTORY[link] = count

def init_aliases(ALIAS : dict[str, str]):
    init(TABLE_ALIASES_NAME, ", ".join(TABLE_ALIASES_COLUMNS_INFO), ", ".join(TABLE_ALIASES_COLUMNS))

    with sqlite3.connect(DATA_DB) as con:
        cur = con.cursor()
        res = cur.execute(f"SELECT * FROM {TABLE_ALIASES_NAME}")
        for name, alias in res.fetchall():
            ALIAS[alias] = name


def add(table_name: str, entry: tuple, n: int):
    with sqlite3.connect(DATA_DB) as con:
        cur = con.cursor()
        cur.execute(f"INSERT INTO {table_name} VALUES ({','.join('?' * n)});", entry)
        con.commit()

def add_song_history(entry: tuple[str, str]):
    add(TABLE_SONG_HISTORY_NAME, entry, 2)

def add_song(song : Song):
    add(TABLE_SONG_NAME, (song.singer, song.title, song.link, song.rating, song.ratingcount), 5)

def add_alias(entry: tuple[str, str]):
    add(TABLE_ALIASES_NAME, entry, 2)


def update_song(song: Song):
    with sqlite3.connect(DATA_DB) as con:
        cur = con.cursor()
        cur.execute(f"UPDATE {TABLE_SONG_NAME} SET ratingcount = ?, rating = ? WHERE link = ? AND title = ? AND singer = ?", 
                    (song.ratingcount, song.rating, song.link, song.title, song.singer))
        con.commit()

def update_song_history(entry: tuple[str, str]):
    with sqlite3.connect(DATA_DB) as con:
        cur = con.cursor()
        cur.execute(f"UPDATE {TABLE_SONG_HISTORY_NAME} SET count = ? WHERE link = ?", list(reversed(entry)))
        con.commit()

def update_aliases(entry: tuple[str, str]):
    with sqlite3.connect(DATA_DB) as con:
        cur = con.cursor()
        cur.execute(f"UPDATE {TABLE_ALIASES_NAME} SET alias = ? WHERE name = ?", list(reversed(entry)))
        con.commit()

def drop_song(song: Song):
    with sqlite3.connect(DATA_DB) as con:
        cur = con.cursor()
        cur.execute(f"DELETE FROM {TABLE_SONG_NAME} WHERE link = ?", (song.link,))
        con.commit()

def drop_alias(entry: tuple[str, str]):
    with sqlite3.connect(DATA_DB) as con:
        cur = con.cursor()
        cur.execute(f"DELETE FROM {TABLE_ALIASES_NAME} WHERE name = ? AND alias = ?", entry)
        con.commit()

def drop_song_history(entry: tuple[str, str]):
    with sqlite3.connect(DATA_DB) as con:
        cur = con.cursor()
        cur.execute(f"DELETE FROM {TABLE_SONG_HISTORY_NAME} WHERE link = ? AND count = ?", entry)
        con.commit()

def edit_alias(old_entry: tuple[str, str], new_entry: tuple[str, str]):
    drop_alias(old_entry)
    add_alias(new_entry)

def edit_song(old_song: Song, new_song: Song):
    drop_song(old_song)
    add_song(new_song)

def edit_song_history(old_entry: tuple[str, str], new_entry: tuple[str, str]):
    drop_song_history(old_entry)
    add_song_history(new_entry)

def reconfigure(ALIASES: dict[str, str], SONGS: list[Song], SONG_LINKS: set[str], SONG_NAMES: dict[str, Song], SONG_HISTORY: dict[str, int]):
    DEBUG = True
    drop_all()
    init_aliases(dict())
    init_songs(list(), set(), dict())
    init_songs_history(dict())
    ALIASES = {}
    for song in SONGS:
        add_song(song)
        ALIASES[song.singer] = song.singer
    for alias in ALIASES:
        add_alias((alias, ALIASES[alias]))
    for link in SONG_HISTORY:
        add_song_history((link, SONG_HISTORY[link]))
    DEBUG = False

def backup():
    if not DEBUG:
        return
    if not os.path.isdir(BACKUP_FOLDER):
        os.mkdir(BACKUP_FOLDER)
    shutil.copyfile(DATA_DB, BACKUP_FOLDER + f"\\{str(random.randint(0, 100))}.db")


def drop_all():
    if not DEBUG:
        return
    backup()
    with sqlite3.connect(DATA_DB) as con:
        cur = con.cursor()
        cur.execute(f"DROP TABLE songs;")
        cur.execute(f"DROP TABLE songs_history;")
        cur.execute(f"DROP TABLE aliases;")

def info_all():
    if not DEBUG:
        return
    with sqlite3.connect(DATA_DB) as con:
        cur = con.cursor()
        for table in cur.execute("SELECT name FROM sqlite_master;").fetchall():
            print(cur.execute(f"PRAGMA table_info({table[0]})").fetchall())
            print(cur.execute(f"SELECT * FROM {table[0]}").fetchall())

if __name__ == '__main__':
    DEBUG = True
    info_all()