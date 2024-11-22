import requests
import re
import json
import bs4
from consts import *
import yt_dlp

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

# test = "towa error"
# with requests.get(SEARCH_LINK, params={'search_query': test}) as r:
#     print(r.encoding)
#     soup = bs4.BeautifulSoup(r.text, 'lxml')
#     with open("html_test.txt", 'w+', encoding='utf-8') as file:
#         file.write(soup.prettify())

#     script = soup.find_all("script")

#     for chunk in script:
#         chunk: bs4.element.Tag
#         if re.search("var ytInitialData =", chunk.text):
#             break
    
#     res = []
#     res_cache = set()
#     for match in re.finditer("/watch\?v=[^\\\\\"]*", chunk.text):
#         if match.group(0) not in res_cache:
#             res_cache.add(match.group(0))
#             res.append(match.group(0))

#     print(res)

# print(query(test))

yt_dl_opt = {
    'quiet': True,
    'ignoreerrors' : True
    # 'format': 'bestaudio',
    # 'outtmpl': f"{song.path()}",
    # 'noplaylist': True,
    # 'postprocessors': [{
    #     'key': 'FFmpegExtractAudio',
    #     'preferredcodec': SONG_EXTENSION
    # }]
}
with yt_dlp.YoutubeDL(yt_dl_opt) as dl:
    metadict = dl.extract_info("https://www.youtube.com/watch?v=llLjylG44DQ", download=False)
    print(list(metadict.keys()))
    print(metadict["channel_id"])
    print(metadict["channel"])
    print(metadict["title"])