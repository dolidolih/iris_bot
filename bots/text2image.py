# coding: utf8
from PIL import Image, ImageFont, ImageDraw
import requests, json, random, os
from io import BytesIO, BufferedReader
from bots.gemini import get_gemini_vision_analyze_image
from helper.ImageHelper import ImageHelper as ih
from helper.BotManager import BotManager
from helper.Admin import is_reply
from irispy2 import ChatContext


RES_PATH = "res/"

def draw_text(chat):
    match chat.message.command:
        case "!텍스트":
            draw_default(chat)
        case "!사진":
            txt = " ".join(chat.message.msg.split(" ")[1:])
            chat.message.msg = f"!텍스트 검색##{txt}##  "
            draw_default(chat)
        case "!껄무새":
            draw_parrot(chat)
        case "!멈춰":
            draw_stop(chat)
        case "!지워":
            draw_rmrf(chat)
        case "!진행":
            draw_gogo(chat)
        case "!말대꾸":
            draw_sungmo(chat)
        case "!텍스트추가":
            add_text(chat)

def draw_default(chat):
    msg = " ".join(chat.message.msg.split(" ")[1:])  
    msg_split = msg.split("##")

    match len(msg_split):
        case 1:
            txt = msg
            check = ""
            img = Image.open(RES_PATH + 'default.jpg')

        case 2:
            img = get_image_from_url(msg_split[0])
            txt = msg_split[1]
            check = get_gemini_vision_analyze_image(msg_plit[0])

        case 3:
            url = get_image_url_from_naver(msg_split[1])
            if url == False:
                chat.reply("사진 검색에 실패했습니다.")
                return None
            
            img = get_image_from_url(url)
            txt = msg_split[2]
            check = get_gemini_vision_analyze_image(url)
        
        case _:
            return None
    
    if "True" in check:
        chat.reply("과도한 노출로 차단합니다.")
        return None
    
    add_default_text(chat, img, txt)

def draw_parrot(chat):
    txt = " ".join(chat.message.msg.split(" ")[1:])
    img = Image.open(RES_PATH + 'parrot.jpg')
    add_default_text(chat, img, txt)

def draw_stop(chat):
    txt = " ".join(chat.message.msg.split(" ")[1:])
    img = Image.open(RES_PATH + 'stop.jpg')
    add_default_text(chat, img, txt)

def draw_gogo(chat):
    color = '#FFFFFF'
    txt = " ".join(chat.message.msg.split(" ")[1:])
    img = Image.open(RES_PATH + 'gogo.png')
    fontsize = 30
    draw = ImageDraw.Draw(img)
    font = ImageFont.FreeTypeFont(RES_PATH+'NotoSansCJK-Bold.ttc', fontsize)
    w, h = multiline_textsize(txt,font=font)
    draw.multiline_text((20, img.size[1]/2-70), u'%s' % txt, font=font, fill=color)

    send_image(chat, img)

def draw_rmrf(chat):
    color = '#000000'
    txt = " ".join(chat.message.msg.split(" ")[1:])
    img = Image.open(RES_PATH + 'rmrf.jpg')
    fontsize = 40
    draw = ImageDraw.Draw(img)
    font = ImageFont.FreeTypeFont(RES_PATH+'GmarketSansBold.otf', fontsize)
    w, h = multiline_textsize(txt,font=font)
    draw.multiline_text((img.size[0]/2-w-130, img.size[1]/2-30), u'%s' % txt, font=font, fill=color)

    send_image(chat, img)

def draw_sungmo(chat):
    color = '#000000'
    txt_split = " ".join(chat.message.msg.split(" ")[1:]).split("##")
    txt1 = txt_split[0]
    txt2 = txt_split[1]
    img = Image.open(RES_PATH + 'sungmo.jpeg')
    fontsize = 60
    draw = ImageDraw.Draw(img)
    font = ImageFont.FreeTypeFont(RES_PATH+'NotoSansCJK-Bold.ttc', fontsize)
    w, h = multiline_textsize(txt1,font=font)
    draw.multiline_text((img.size[0]/2-w/2-5, 60), u'%s' % txt1, font=font, fill=color)

    w, h = multiline_textsize(txt2,font=font)
    draw.multiline_text((img.size[0]/2-w/2+5, img.size[1]-170), u'%s' % txt2, font=font, fill=color)
    
    send_image(chat, img)

@is_reply()
def add_text(chat):
    attachment = json.loads(chat.message.attachment)
    bot = BotManager().get_current_bot()
    src_record = bot.api.query("select * from chat_logs where id = ?",[attachment["src_logId"]])[0]
    photo_url = ih.get_photo_url(src_record)

    img = get_image_from_url(photo_url)
    txt = " ".join(chat.message.msg.split(" ")[1:])

    add_default_text(chat, img, txt)

def add_default_text(chat, img, txt):
    if "::" in txt:
        option_split = txt.split('::')
        txt = option_split[0]
        color = '#' + option_split[1]
    else:
        color = '#ffffff'

    fontsize = get_max_font_size(img.size[0],"아"*10, RES_PATH+'GmarketSansBold.otf', max_search_size=500)
    font = ImageFont.FreeTypeFont(RES_PATH+'GmarketSansBold.otf', fontsize)
    
    draw = ImageDraw.Draw(img)
    w, h = multiline_textsize(txt,font=font)
    
    draw.multiline_text((img.size[0]/2-w/2-1, img.size[1]-h-20-1), u'%s' % txt, font=font, align='center', fill="black")
    draw.multiline_text((img.size[0]/2-w/2+1, img.size[1]-h-20-1), u'%s' % txt, font=font, align='center', fill="black")
    draw.multiline_text((img.size[0]/2-w/2-1, img.size[1]-h-20+1), u'%s' % txt, font=font, align='center', fill="black")
    draw.multiline_text((img.size[0]/2-w/2+1, img.size[1]-h-20+1), u'%s' % txt, font=font, align='center', fill="black")
    draw.multiline_text((img.size[0]/2-w/2, img.size[1]-h-20), u'%s' % txt, font=font, align='center', fill=color)
    
    send_image(chat, img)
    

def send_image(chat, img):
    image_bytes_io = BytesIO()
    img = img.convert("RGBA")
    img.save(image_bytes_io, format="PNG")
    image_bytes_io.seek(0)
    buffered_reader = BufferedReader(image_bytes_io)
    chat.reply_media(
        "IMAGE",
        [buffered_reader]
    )

def get_image_from_url(url):
    try:
        response = requests.get(url)
    except:
        if url[-3:] == 'jpg':
            response = requests.get(url[:-3]+'png')
        elif url[-3:] == 'png':
            response = requests.get(url[:-3]+'jpg')
    img = Image.open(BytesIO(response.content))
    img = img.convert("RGBA")
    return img

def get_image_url_from_naver(query):
    url = 'https://openapi.naver.com/v1/search/image'
    headers = {
        'X-Naver-Client-Id': os.getenv("X_NAVER_CLIENT_ID"),
        'X-Naver-Client-Secret': os.getenv("X_NAVER_CLIENT_SECRET")
        }
    params = {
        'query' : query,
        'display':'20'
        }
    res = requests.get(url,params=params, headers=headers)
    
    js = json.loads(res.text)['items']
    link = []
    if not len(js) == 0:
        for item in js:
            if not "medium.com" in item['link'] and not "post.phinf.naver.net" in item['link']:
                link.append(item['link'])
        if len(link) == 0:
            return js[random.randint(0,len(js))]['link']
        else:
            return link[random.randint(0,len(link)-1)]
    else:
        return False
  
def get_max_font_size(image_width, text, font_path, max_search_size=500):
    target_width = image_width
    low = 1
    high = max_search_size
    best_size = None

    while low <= high:
        mid = (low + high) // 2
        font = ImageFont.FreeTypeFont(font_path, mid)
        w, h = multiline_textsize(text, font=font)

        if w <= target_width:
            best_size = mid
            low = mid + 1
        else:
            high = mid - 1

    return best_size

def multiline_textsize(text,font):
    total_width = 0
    total_height = 0

    lines = text.splitlines()

    for line in lines:
        bbox = font.getbbox(line)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        total_width = max(total_width, w)
        total_height += h

    return (w, h)