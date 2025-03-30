from irispy2 import Bot, ChatContext
import asyncio
from gemini_webapi import GeminiClient
import time
import json
from helper.Admin import has_param
import os

Secure_1PSID = os.getenv("SECURE_1PSID")
Secure_1PSIDTS = os.getenv("SECURE_1PSIDTS")

@has_param()
def get_imagen(chat: ChatContext):
    image_files = asyncio.run(get_client(chat.message.msg[4:]))
    images = []
    for file in image_files:
        images.append(open("/home/dolidoli/res/temppic/"+file,"rb"))
    chat.reply_media(
        "IMAGE",
        images
    )

async def get_client(msg: str):
    client = GeminiClient(Secure_1PSID, Secure_1PSIDTS, proxy=None)
    await client.init(timeout=30, auto_close=False, close_delay=300, auto_refresh=False, verbose=True)
    response = await client.generate_content(msg)
    filenames = []
    for i, image in enumerate(response.images):
        filename = str(time.time()) + '.png'
        await image.save(path="/home/dolidoli/res/temppic/", filename=filename, verbose=True)
        filenames.append(filename)
    
    return filenames