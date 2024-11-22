import os

DEFAULT_LINK = "https://www.youtube.com"
SEARCH_LINK = "https://www.youtube.com/results"
DATA_FOLDER = "data"
SONG_EXTENSION = "wav"
DELIMITER = "\t"
YES = "✅"
NO = "❎"
RANDOM_MIN = 0
RANDOM_MAX = 1000000000
MAX_DURATION = 600


DATA_TXT = os.path.join(DATA_FOLDER, "data.txt")
DATA_SONGS = os.path.join(DATA_FOLDER, "songs")
DATA_HISTORY = os.path.join(DATA_FOLDER, "history.txt")
DATA_TEMP = os.path.join(DATA_FOLDER, "tmp")