import discord
from consts import *

class Song:
    singer: str
    title: str
    link: str
    rating: float
    ratingcount: int
    temp: bool

    def __init__(self, singer: str, title: str, link: str, rating: float, ratingcount: int, temp: bool = False):
        self.singer = singer
        self.title = title
        self.link = link
        self.rating = rating
        self.ratingcount = ratingcount
        self.temp = temp

    def __str__(self):
        return f"{self.singer}-{self.title}: {str(self.getAvgRating())}"
    
    def name(self) -> str:
        return self.link if self.temp else Song.format(self.singer, self.title)
    
    def path(self) -> str:
        return os.path.join(DATA_TEMP, f"{self.singer}-{self.title}") if self.temp else os.path.join(DATA_SONGS, f"{self.singer}-{self.title}") 
    
    def pathWithExtension(self) -> str:
        return self.path() + "." + SONG_EXTENSION
    
    def TEMP_SONG(key: int, link: str):
        return Song("", str(key), link, 0, 0, True)
    
    def format(singer: str, title: str) -> str:
        return f"{singer}-{title}"
    
    def getAvgRating(self) -> str:
        if self.ratingcount == 0:
            return "unrated"
        else:
            return str(self.rating/self.ratingcount)
        
    def __copy__(self):
        return Song(self.singer, self.title, self.link, self.rating, self.ratingcount)
    

class PlayingQueue:
    guild: int
    vc_client: discord.VoiceClient
    vc: discord.VoiceState
    playingQueue: list[Song]
    playing: bool
    skip: bool

    def __init__(self, guild_id: int, vc: discord.VoiceState):
        self.guild = guild_id
        self.vc_client = None
        self.vc = vc
        self.playingQueue = []
        self.playing = False
        self.skip = False