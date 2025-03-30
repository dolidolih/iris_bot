from helper.Admin import is_admin, is_reply
from helper.DatabaseHelper import get_reply_user_id
from irispy2 import ChatContext
from helper.BotManager import BotManager

@is_admin()
@is_reply()
def ban_user(chat: ChatContext):
    reply_user_id = get_reply_user_id(chat)
    kv = BotManager().get_kv()
    ban_list = kv.get('ban')
    if reply_user_id in ban_list:
        chat.reply("이미 밴 등록된 유저입니다.")
    else:
        ban_list.append(reply_user_id)
        print(ban_list)
        kv.put('ban',ban_list)
        chat.reply("유저를 밴 목록에 등록하였습니다.")

@is_admin()
@is_reply()
def unban_user(chat: ChatContext):
    reply_user_id = get_reply_user_id(chat)
    kv = BotManager().get_kv()
    ban_list: list = kv.get('ban')
    if reply_user_id in ban_list:
        ban_list.remove(reply_user_id)
        kv.put('ban',ban_list)
        chat.reply("밴 목록에서 삭제하였습니다.")
        print(kv.get('ban'))
    else:
        chat.reply("밴 목록에 없는 유저입니다.")
