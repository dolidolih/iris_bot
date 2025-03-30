from helper.DatabaseHelper import get_reply_user_id
from irispy2 import ChatContext, Bot
from helper.BotManager import BotManager

import json

def is_admin():
    def decorator(func):
        def wrapper(*args,**kwargs):
            chat = args[0]
            return func(*args, **kwargs) if admin_check(chat) else None
        return wrapper
    return decorator

def is_reply():
    def decorator(func):
        def wrapper(*args,**kwargs):
            chat: ChatContext = args[0]
            return func(*args, **kwargs) if chat.message.type == 26 else None
        return wrapper
    return decorator

def is_not_banned():
    def decorator(func):
        def wrapper(*args,**kwargs):
            chat: ChatContext = args[0]
            if admin_check(chat):
                return func(*args, **kwargs)
            kv = BotManager().get_kv()
            res = chat.sender.id in kv.get('ban')
            return "" if res else func(*args, **kwargs)
        return wrapper
    return decorator

def on_message_chat_addon():
    def decorator(func):
        def wrapper(*args,**kwargs):
            chat: ChatContext = args[0]
            msg_split = chat.message.msg.split(" ")
            chat.message.command = msg_split[0]
            chat.message.has_param = True if len(msg_split) > 1 else False
            return func(chat)
        return wrapper
    return decorator

def has_param():
    def decorator(func):
        def wrapper(*args,**kwargs):
            chat: ChatContext = args[0]
            return func(*args, **kwargs) if chat.message.has_param else None
        return wrapper
    return decorator

def admin_check(chat:ChatContext):
    kv = BotManager().get_kv()
    res = chat.sender.id in kv.get('admin')
    return res
