from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
from helper.ImageHelper import ImageHelper as ih
from helper.Admin import has_param
from irispy2 import Bot, ChatContext
from helper.BotManager import BotManager
import json
from loguru import logger
import os

pro_key = os.getenv("GEMINI_KEY")

safety_settings=[
    types.SafetySetting(
        category="HARM_CATEGORY_HARASSMENT",
        threshold="BLOCK_NONE",  # Block none
    ),
    types.SafetySetting(
        category="HARM_CATEGORY_HATE_SPEECH",
        threshold="BLOCK_NONE",  # Block none
    ),
    types.SafetySetting(
        category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
        threshold="BLOCK_ONLY_HIGH",  # Block few
    ),
    types.SafetySetting(
        category="HARM_CATEGORY_DANGEROUS_CONTENT",
        threshold="BLOCK_NONE",  # Block none
    ),
    types.SafetySetting(
        category="HARM_CATEGORY_CIVIC_INTEGRITY",
        threshold="BLOCK_NONE",  # Block none
    ),
]

@has_param()
def get_gemini_image(chat : ChatContext):
    try:
        msg = chat.message.msg[4:]
        client = genai.Client(
            api_key=pro_key,
        )

        model = "gemini-2.0-flash-exp-image-generation"
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=msg),
                ],
            ),
        ]
        generate_content_config = types.GenerateContentConfig(
            response_modalities=[
                "image",
                "text",
            ],
            safety_settings=safety_settings
        )

        res = ""

        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            if not chunk.candidates or not chunk.candidates[0].content or not chunk.candidates[0].content.parts:
                continue
            if chunk.candidates[0].content.parts[0].inline_data:
                chat.reply_media(
                "IMAGE",
                [BytesIO(chunk.candidates[0].content.parts[0].inline_data.data)]
                )
                return ""

            elif chunk.candidates[0].content.parts[0].text:
                res = res + chunk.candidates[0].content.parts[0].text

        if res.strip() != "":
            chat.reply(
                res.strip()
            )
        else:
            chat.reply(
                f"오류가 발생하였거나, Gemini가 이미지 생성을 거부하였습니다.\n"
                f"Q: {chat.message.msg[4:]}"
            )
    except:
        chat.reply(
            f"오류가 발생하였거나, Gemini가 이미지 생성을 거부하였습니다.\n"
            f"Q: {chat.message.msg[4:]}"
        )

@has_param()
def get_gemini_image_to_image(chat : ChatContext):
    try:
        if chat.message.type != 26:
            chat.reply("메세지에 답장하여 요청하세요")
            return ""
        
        msg = chat.message.msg[5:]
        attachment = json.loads(chat.message.attachment)
        bot = BotManager().get_current_bot()
        src_record = bot.api.query("select * from chat_logs where id = ?",[attachment["src_logId"]])[0]
        photo_url = ih.get_photo_url(src_record)
        img = ih.download_img_from_url(photo_url)
        filepath = ih.save_img(img)

        client = genai.Client(
            api_key=pro_key,
        )

        file_ref = client.files.upload(file=filepath)

        model = "gemini-2.0-flash-exp-image-generation"
        contents = [msg, file_ref]
        generate_content_config = types.GenerateContentConfig(
            response_modalities=[
                "image",
                "text",
            ],
            safety_settings=safety_settings
        )

        res = ""

        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            if not chunk.candidates or not chunk.candidates[0].content or not chunk.candidates[0].content.parts:
                continue

            if chunk.candidates[0].content.parts[0].inline_data:
                chat.reply_media(
                "IMAGE",
                [BytesIO(chunk.candidates[0].content.parts[0].inline_data.data)]
                )
                return ""

            elif chunk.candidates[0].content.parts[0].text:
                res = res + chunk.candidates[0].content.parts[0].text

        if res.strip() != "":
            chat.reply(
                res.strip()
            )
        else:
            chat.reply(
                f"오류가 발생하였거나, Gemini가 이미지 생성을 거부하였습니다.\n"
                f"Q: {chat.message.msg[4:]}"
            )
    except:
        chat.reply(
            f"오류가 발생하였거나, Gemini가 이미지 생성을 거부하였습니다.\n"
            f"Q: {chat.message.msg[4:]}"
        )