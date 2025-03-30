from irispy2 import ChatContext, Bot
from helper.BotManager import BotManager
import json

def get_reply_user_id(chat: ChatContext):
    bot = BotManager().get_current_bot()
    src_log_id = json.loads(chat.message.attachment)['src_logId']
    query = "select * from chat_logs where id = ?"
    
    src_record = bot.api.query(query,[src_log_id])
    src_user_id = src_record[0]['user_id']

    return int(src_user_id)