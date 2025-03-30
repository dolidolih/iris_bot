import requests
import urllib.parse
from irispy2 import ChatContext

def find_lyrics(chat: ChatContext):
    try:
        query = urllib.parse.quote_plus(chat.message.msg[6:])
        url = f"https://apis.naver.com/vibeWeb/musicapiweb/v4/search/lyric?query={query}&start=1&display=10&sort=RELEVANCE"
        r = requests.get(
                url,
                headers={'Accept': 'application/json'}
                ).json()
        songs = r["response"]["result"]["tracks"][0:5]
        res = [f'{i+1}. {s["artists"][0]["artistName"]} - {s["trackTitle"]}' for i,s in enumerate(songs)]
        chat.reply("\n".join(res))
    except:
        chat.reply("검색된 노래가 없습니다.")

def get_lyrics(chat: ChatContext):
    try:
        query = urllib.parse.quote_plus(chat.message.msg[6:])
        url = f"https://apis.naver.com/vibeWeb/musicapiweb/v4/searchall?query={query}&sort=RELEVANCE&vidDisplay=25&trDisplay=9&alDisplay=21&arDisplay=21"
        r = requests.get(
                url,
                headers={'Accept': 'application/json'}
                ).json()
        track = r["response"]["result"]["trackResult"]["tracks"][0]
        res = f'{track["artists"][0]["artistName"]} - {track["trackTitle"]}\n' + "\u200b"*500 + "\n"
        track_url = f'https://apis.naver.com/vibeWeb/musicapiweb/vibe/v4/lyric/{track["trackId"]}'
        r2 = requests.get(
                track_url,
                headers={'Accept': 'application/json'}
                ).json()
        res += r2["response"]["result"]["lyric"]["normalLyric"]["text"]
        chat.reply(res)
    except Exception as e:
        chat.reply("검색된 노래가 없습니다.")
        print(e)