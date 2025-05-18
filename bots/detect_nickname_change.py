import time, datetime
from iris import PyKV, Bot
import pytz

detect_rooms = ["18398338829933617"]
refresh_second = 3

def detect_nickname_change(base_url):
    bot = Bot(base_url)
    kv = PyKV()
    query = "select enc,nickname,user_id,involved_chat_id from db2.open_chat_member"
    history = kv.get('user_history')
    members = {}
    
    if not history:
        query_result = bot.api.query(query=query, bind=[])
        history = {}
        for member in query_result:
            history[member['user_id']] = {"history": [{
                "nickname":member["nickname"],
                "involved_chat_id":member["involved_chat_id"],
                "date":""
            }]
            }
        kv.put('user_history',history)
    
    while True:
        try:
            changed = False
            query_result = bot.api.query(query=query, bind=[])
            members = {}
            for member in query_result:
                members[member['user_id']] = {"nickname":member["nickname"],"involved_chat_id":member["involved_chat_id"]}
            
            for user_id in members.keys():
                if user_id not in history:
                    history[user_id] = {"history" : [{
                        "nickname":members[user_id]["nickname"],
                        "involved_chat_id":members[user_id]["involved_chat_id"],
                        "date": ""
                    }]
                    }   
            for user_id in history.keys():
                user = history[user_id]["history"][-1]
                new_user = members[user_id]
                if user["nickname"] != new_user["nickname"]:
                    korean = pytz.timezone('Asia/Seoul')
                    time_string = datetime.datetime.now(korean).strftime("%y%m%d %H:%M")
                    history[user_id]["history"].append(
                        {
                            "nickname":new_user["nickname"],
                            "involved_chat_id":new_user["involved_chat_id"],
                            "date":time_string
                        }
                    )
                    
                    if user["involved_chat_id"] in detect_rooms:
                        user_history = []
                        for change in history[user_id]["history"]:
                            user_history.append(f"ㄴ{'[' + change['date'] + ']' if not change['date'] == '' else ''} {change['nickname']}")
                        
                        user_history.reverse()
                        history_string = "\n".join(user_history)
                        
                        message = f"닉네임이 변경되었어요!\n{user['nickname']} -> {new_user['nickname']}\n" + "\u200b"*600 + "\n" + history_string
                        
                        bot.api.reply(int(new_user["involved_chat_id"]),message.strip())
                    changed = True
            if changed:
                kv.put('user_history',history)
        except Exception as e:
            print("something went wrong")
            print(e)
        
        time.sleep(refresh_second)