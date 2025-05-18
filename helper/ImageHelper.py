import requests
import time
from PIL import Image
from io import BytesIO, BufferedReader
from loguru import logger

class ImageHelper:
    image_directory = "res/temppic/"
    
    @classmethod
    def get_photo_url(cls, chat) -> list:        
        try:
            urls = []
            if chat.message.type == 71:
                for item in chat.message.attachment["C"]["THL"]:
                    urls.append(item["TH"]["THU"])
            elif chat.message.type == 27:
                for item in chat.message.attachment["imageUrls"]:
                    urls.append(item)
            else:
                urls.append(chat.message.attachment["url"])
            return urls
        except Exception as e:
            return None

    @classmethod
    def download_img_from_url(cls, urls) -> list:
        try:
            if type(urls) == str:
                urls = [urls]
            result = []
            for url in urls:
                result.append(requests.get(url).content)
            return result
        except Exception as e:
            print(e)
            return None

    @classmethod
    def save_img(cls, byte_img) -> str :
        try:
            img = Image.open(BytesIO(byte_img))
            img.convert("RGBA")
            filepath = cls.image_directory + str(time.time()) + ".png"
            img.save(filepath,"png")
            return filepath
        except Exception as e:
            print(e)
            return None

    @classmethod
    def send_image(cls, chat, imgs: list):
        chat.reply_media(
            imgs
        )

    @classmethod
    def get_image_from_url(cls, url: str) -> Image:
        response = cls.download_img_from_url(url)[0]
        img = Image.open(BytesIO(response))
        img = img.convert("RGBA")
        return img

    @classmethod
    def image_to_buffered_reader(cls, img: Image) -> BufferedReader:
        image_bytes_io = BytesIO()
        img = img.convert("RGBA")
        img.save(image_bytes_io, format="PNG")
        image_bytes_io.seek(0)
        buffered_reader = BufferedReader(image_bytes_io)
        return buffered_reader
