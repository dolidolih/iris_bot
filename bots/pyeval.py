# coding: utf8
import sys
import subprocess
from iris import ChatContext
from iris.decorators import *

@is_admin
@has_param
def python_eval(chat: ChatContext):
    with open('temp.py', 'w') as tp:
        tp.write(chat.message.msg[5:])
    try:
        exec_out = subprocess.check_output([".venv/bin/python", "temp.py"],stderr=subprocess.PIPE,timeout=30).decode("utf-8")
        if exec_out[-1:] == "\n":
                exec_out = exec_out[:-1]
    except subprocess.TimeoutExpired:
        exec_out = "timed out"
    except subprocess.CalledProcessError as e:
        exec_out = e.stderr.decode("utf-8")
        exec_out = exec_out[str(exec_out).find("line"):-1]
    print(exec_out)
    chat.reply(exec_out)

@is_admin
@has_param
def real_eval(chat: ChatContext, kl):
    try:
        exec(chat.message.msg[5:])
    except Exception as e:
        chat.reply(e)
