from irispy2 import Bot, ChatContext
from irispy2.bot.models import ErrorContext
from bots.gemini import get_gemini_image, get_gemini_image_to_image
from bots.pyeval import python_eval, real_eval
from bots.stock import create_stock_image
from bots.imagen import get_imagen
from bots.lyrics import get_lyrics, find_lyrics
from helper.Admin import is_not_banned, on_message_chat_addon
from helper.BanControl import ban_user, unban_user
from helper.BotManager import BotManager
import sys

iris_url = sys.argv[1]
bot = BotManager(iris_url).get_current_bot()

@bot.on_event("message")
@is_not_banned()
@on_message_chat_addon()
def on_message(chat: ChatContext):
    try:
        match chat.message.command:
            
            case "!hhi":
                chat.reply(f"Hello {chat.sender.name}")

            case "!tt":
                chat.reply_media("IMAGE", [open("/home/dolidoli/aaa.jpeg", "rb")])

            case "!ttt":
                chat.reply_media("IMAGE", [open("/home/dolidoli/aaa.jpeg", "rb"), open("/home/dolidoli/aaa.jpeg", "rb"), open("/home/dolidoli/aaa.jpeg", "rb")])
            
            case "!iris":
                chat.reply_media("IMAGE", [open("/home/dolidoli/help.png", "rb")])

            case "!gi":
                get_gemini_image(chat)
            
            case "!i2i":
                get_gemini_image_to_image(chat)
            
            case "!ipy":
                python_eval(chat)
            
            case "!iev":
                real_eval(chat)
            
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
            
    except Exception as e :
        print(e)
    finally:
        BotManager().close_kv_connection()
        sys.stdout.flush()
            
    

@bot.on_event("error")
def on_error(err: ErrorContext):
    print(err.event, "이벤트에서 오류가 발생했습니다", err.exception)
    #sys.stdout.flush()


if __name__ == "__main__":
    bot.run()
