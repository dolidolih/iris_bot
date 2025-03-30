import requests
import time
from PIL import Image
from io import BytesIO
from loguru import logger
import json

class ImageHelper:
    image_directory = "/home/dolidoli/res/temppic/"
    
    @classmethod
    def get_photo_url(cls, record):
        attachment = json.loads(record["attachment"])
        try:
            if record["type"] == 71:
                url = attachment["C"]["THL"][0]["TH"]["THU"]
            elif record["type"] == 27:
                url = attachment["imageUrls"][0]
            else:
                url = attachment["url"]
            return url
        except Exception as e:
            print(e)
            return None

    @classmethod
    def download_img_from_url(cls, url):
        try:
            res = requests.get(url)
            return res.content
        except Exception as e:
            print(e)
            return None

    @classmethod
    def save_img(cls, byte_img):
        try:
            img = Image.open(BytesIO(byte_img))
            img.convert("RGBA")
            filepath = cls.image_directory + str(time.time()) + ".png"
            img.save(filepath,"png")
            return filepath
        except Exception as e:
            print(e)
            return None