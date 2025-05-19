from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import requests
from iris.decorators import *
from iris import ChatContext
import os, io
import time

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

def get_gemini(chat: ChatContext):
    match chat.message.command:
        case "!gi":
            get_gemini_image(chat)

        case "!i2i":
            get_gemini_image_to_image(chat)
        
        case "!분석":
            get_gemini_vision_analyze_image_reply(chat)

@has_param
def get_gemini_image(chat : ChatContext):
    try:
        msg = chat.message.param
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

@is_reply
@has_param
def get_gemini_image_to_image(chat : ChatContext):
    try:
        msg = chat.message.param
        src_chat = chat.get_source()
        if src_chat.message.image:
            img = src_chat.message.image.img[0]
        else:
            return
        
        client = genai.Client(
            api_key=pro_key,
        )

        model = "gemini-2.0-flash-exp-image-generation"
        contents = [msg, img]
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
                f"Q: {chat.message.param}"
            )
    except Exception as e:
        print(chat.image)
        import traceback
        traceback.print_exc()
        chat.reply(
            f"오류가 발생하였거나, Gemini가 이미지 생성을 거부하였습니다.\n"
            f"Q: {chat.message.param}"
        )

@is_reply
def get_gemini_vision_analyze_image_reply(chat: ChatContext):
    src_chat = chat.get_source()
    if hasattr(src_chat, "image"):
        img = src_chat.image.img[0]
        check_result = get_gemini_vision_analyze_image(img)
        chat.reply(check_result)

def get_gemini_vision_analyze_image(img):
    client = genai.Client(api_key=pro_key)
    res = client.models.generate_content(
        model="gemini-2.0-flash-exp-image-generation",
        config=types.GenerateContentConfig(
            system_instruction="analyze the given image, and rate violence, sexuality score out of 100 in below format. If the image given is text-only image, scores must be N/A. If sexuality score is over 50, 성인물 will be True. Do not add any other comments or markdown\n폭력성 : score/100\n선정성 : score/100\n성인물 : True/False",
            tools=[types.Tool(
                google_search=types.GoogleSearchRetrieval(
                    dynamic_retrieval_config=types.DynamicRetrievalConfig(
                        dynamic_threshold=0.6))
            )],),
        contents=[img]
        )
    try:
        result = res.text.strip()
    except:
        result = "Gemini 서버에서 오류가 발생했거나 분당 한도가 초과하였습니다. 잠시 후 다시 시도해주세요."
    return result
