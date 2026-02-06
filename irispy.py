from iris import ChatContext, Bot
from iris.bot.models import ErrorContext
from bots.gemini import get_gemini
from bots.pyeval import python_eval, real_eval
from bots.stock import create_stock_image
from bots.imagen import get_imagen
from bots.lyrics import get_lyrics, find_lyrics
from bots.replyphoto import reply_photo
from bots.text2image import draw_text
from bots.coin import get_coin_info

from iris.decorators import *
from helper.BanControl import ban_user, unban_user
from iris.kakaolink import IrisLink

from bots.detect_nickname_change import detect_nickname_change
import sys, threading
import signal
import time
import os

iris_url = os.getenv("IRIS_URL")
if not iris_url:
    if len(sys.argv) > 1:
        iris_url = sys.argv[1]
    else:
        # Default fallback or error
        print("Warning: IRIS_URL not set. Usage: python irispy.py <url> or set IRIS_URL env var.")
        # We allow it to fail later or handle it gracefully if needed, 
        # but for now let's exit if we strictly need it, or assume user knows what they are doing.
        if len(sys.argv) <= 1: 
             print("Error: No IRIS_URL provided.")
             sys.exit(1)

bot = Bot(iris_url)

# Graceful shutdown handler
def signal_handler(sig, frame):
    print("\nAttempting graceful shutdown...")
    # Add any specific cleanup code here if `bot` has a close method exposed
    # For now, we exit, which usually closes sockets. 
    # If the library supports explicit close provided by user, call it here.
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

@bot.on_event("message")
@is_not_banned
def on_message(chat: ChatContext):
    try:
        match chat.message.command:
            
            case "!hhi":
                chat.reply(f"Hello {chat.sender.name}")

            case "!tt" | "!ttt" | "!프사" | "!프사링":
                reply_photo(chat, kl)

            #make your own help.png or remove !iris
            case "!iris":
                chat.reply_media("res/help.png")

            case "!gi" | "!i2i" | "!분석":
                get_gemini(chat)
            
            case "!ipy":
                python_eval(chat)
            
            case "!iev":
                real_eval(chat, kl)
            
            case "!ban":
                ban_user(chat)
            
            case "!unban":
                unban_user(chat)

            case "!주식":
                create_stock_image(chat)

            case "!ig":
                get_imagen(chat)
            
            case "!가사찾기":
                find_lyrics(chat)

            case "!노래가사":
                get_lyrics(chat)

            case "!텍스트" | "!사진" | "!껄무새" | "!멈춰" | "!지워" | "!진행" | "!말대꾸" | "!텍스트추가":
                draw_text(chat)
            
            case "!코인" | "!내코인" | "!바낸" | "!김프" | "!달러" | "!코인등록" | "!코인삭제":
                get_coin_info(chat)
            
    except Exception as e :
        print(e)

#입장감지
@bot.on_event("new_member")
def on_newmem(chat: ChatContext):
    #chat.reply(f"Hello {chat.sender.name}")
    pass

#퇴장감지
@bot.on_event("del_member")
def on_delmem(chat: ChatContext):
    #chat.reply(f"Bye {chat.sender.name}")
    pass


@bot.on_event("error")
def on_error(err: ErrorContext):
    print(err.event, "이벤트에서 오류가 발생했습니다", err.exception)
    #sys.stdout.flush()

if __name__ == "__main__":
    #닉네임감지를 사용하지 않는 경우 주석처리
    nickname_detect_thread = threading.Thread(target=detect_nickname_change, args=(bot.iris_url,))
    nickname_detect_thread.start()
    #카카오링크를 사용하지 않는 경우 주석처리
    #카카오링크를 사용하지 않는 경우 주석처리
    kl = IrisLink(bot.iris_url)
    
    # Reconnection Loop
    while True:
        try:
            print(f"Connecting to IRIS at {bot.iris_url}...")
            bot.run()
        except Exception as e:
            print(f"Bot/Connection crashed: {e}")
            print("Reconnecting in 5 seconds...")
            time.sleep(5)
        except SystemExit:
            print("Bot stopped gracefully.")
            break
