import requests
from PIL import Image, ImageDraw, ImageFont
import io
import json
import pandas as pd
import mplfinance as mpf
import matplotlib.dates as mdates
from helper.Admin import has_param

@has_param()
def create_stock_image(chat):
    """
    Generates a PNG image with stock information based on the given query.
    """
    try:
        # 1. Fetch stock code
        query = chat.message.msg[4:]
        autocomplete_url = f"https://ac.stock.naver.com/ac?q={query}&target=stock%2Cipo%2Cindex%2Cmarketindicator"
        autocomplete_response = requests.get(autocomplete_url)
        autocomplete_response.raise_for_status()
        autocomplete_json = autocomplete_response.json()

        if not autocomplete_json['items'] or not autocomplete_json['items'][0]:
            chat.reply("종목을 찾는데 실패했습니다.")
            return None
        
        type_code = autocomplete_json['items'][0]['typeCode']
        if not type_code in ["KOSPI","KOSDAQ"]:
            chat.reply("현재는 국내 주식시장만 지원합니다.")
            return None

        stock_code = autocomplete_json['items'][0]["code"]
        stock_name = autocomplete_json['items'][0]["name"]

        # 2. Fetch stock chart image
        chart_url = f"https://ssl.pstatic.net/imgfinance/chart/item/area/day/{stock_code}.png"
        chart_response = requests.get(chart_url, stream=True)
        chart_response.raise_for_status()

        chart_image = Image.open(io.BytesIO(chart_response.content)).convert("RGBA")
        #chart_image = create_candlestick_chart(test_json)
        chart_width, chart_height = chart_image.size

        # 3. Fetch real-time stock data
        realtime_url = f"https://polling.finance.naver.com/api/realtime?query=SERVICE_RECENT_ITEM:{stock_code}"
        realtime_response = requests.get(realtime_url)
        realtime_response.raise_for_status()
        realtime_json = realtime_response.json()

        if realtime_json['resultCode'] != 'success' or not realtime_json['result']['areas'] or not realtime_json['result']['areas'][0]['datas']:
            return None

        stock_data = realtime_json['result']['areas'][0]['datas'][0]

        # 4. Create white area and paste chart
        new_height = 550
        new_image = Image.new("RGB", (chart_width, new_height), "white")
        new_image.paste(chart_image, (0, new_height - chart_height), chart_image)

        # 5. Add stock information
        draw = ImageDraw.Draw(new_image)
        try:
            font_path = "res/GmarketSansMedium.otf"
            font_size_title = 40
            font_size_code = 18
            font_size_normal = 30
            font_title = ImageFont.truetype(font_path, font_size_title)
            font_code = ImageFont.truetype(font_path, font_size_code)
            font_normal = ImageFont.truetype(font_path, font_size_normal)

        except IOError as e:
            print(f"IOError during font loading: {e}")
            font_title = ImageFont.load_default()
            font_code = ImageFont.load_default()
            font_normal = ImageFont.load_default()


        text_color = (0, 0, 0)

        # Stock Name and Code
        title_text = stock_name
        code_text = stock_code

        title_x, title_y = 15, 15
        draw.text((title_x, title_y), title_text, font=font_title, fill=text_color)

        title_bbox = font_title.getbbox(title_text)
        code_bbox = font_code.getbbox(code_text)

        code_x = title_x + title_bbox[2] + 10 # position code after name with spacing
        code_y = title_y + title_bbox[3] - code_bbox[3] # bottom align code with name

        draw.text((code_x, code_y), code_text, font=font_code, fill=text_color)


        # Current Price and Change
        current_price_text = f"{stock_data['nv']:,}"
        change_text = f"{stock_data['cv']:,}"
        change_rate_text = f"{stock_data['cr']:.2f}%"

        price_x = 15
        price_y = code_y + code_bbox[3] + 30 # position price after code line. No change needed for bottom align of price line itself
        change_color = (255, 0, 0) if stock_data['rf'] == '2' else (0, 0, 255) if stock_data['rf'] == '5' else text_color
        current_price_color = change_color if stock_data['rf'] != '0' else text_color

        draw.text((price_x, price_y), current_price_text, font=font_title, fill=current_price_color)
        price_bbox = font_title.getbbox(current_price_text)
        price_bottom_y = price_y + price_bbox[3]

        change_symbol = "▲" if stock_data['rf'] == '2' else "▼" if stock_data['rf'] == '5' else ""
        change_x = price_x + font_title.getlength(current_price_text) + 10

        change_symbol_bbox = font_normal.getbbox(change_symbol)
        change_text_bbox = font_normal.getbbox(change_text)
        change_rate_text_bbox = font_normal.getbbox(change_rate_text)

        change_symbol_y = price_bottom_y - change_symbol_bbox[3]
        change_text_y = price_bottom_y - change_rate_text_bbox[3]
        change_rate_text_y = price_bottom_y - change_rate_text_bbox[3]


        draw.text((change_x, change_symbol_y), change_symbol, font=font_normal, fill=change_color)
        draw.text((change_x + font_normal.getlength(change_symbol), change_text_y), change_text, font=font_normal, fill=change_color)
        draw.text((change_x + font_normal.getlength(change_symbol + change_text) + 15, change_rate_text_y), change_rate_text, font=font_normal, fill=change_color)


        # Previous Day, High, Volume etc.
        info_x_start_label = 15
        info_x_start_value = 90
        info_y_start = price_y + font_title.getbbox(current_price_text)[3] + 30
        line_height = 32
        info_margin = 220

        # First column (전일, 시가, 저가)
        draw.text((info_x_start_label, info_y_start), "전일", font=font_normal, fill=text_color)
        draw.text((info_x_start_label, info_y_start + line_height), "시가", font=font_normal, fill=text_color)
        draw.text((info_x_start_label, info_y_start + 2 * line_height), "저가", font=font_normal, fill=text_color)

        draw.text((info_x_start_value, info_y_start), f"{stock_data['pcv']:,}", font=font_normal, fill=text_color)
        draw.text((info_x_start_value, info_y_start + line_height), f"{stock_data['ov']:,}", font=font_normal, fill=text_color)
        draw.text((info_x_start_value, info_y_start + 2 * line_height), f"{stock_data['lv']:,}", font=font_normal, fill=text_color)


        # Second column (고가, 거래량, 거래대금) - Aligned values
        info_x_start_label_col2 = info_x_start_value + info_margin
        info_x_start_value_col2 = info_x_start_label_col2 + 150

        draw.text((info_x_start_label_col2, info_y_start), "고가", font=font_normal, fill=text_color)
        draw.text((info_x_start_label_col2, info_y_start + line_height), "거래량", font=font_normal, fill=text_color)
        draw.text((info_x_start_label_col2, info_y_start + 2 * line_height), "거래대금", font=font_normal, fill=text_color)


        high_price_text = f"{stock_data['hv']:,}"
        volume_text = f"{stock_data['aq']:,}"
        transaction_amount_text = f"{int(stock_data['aa']/1000000):,} 백만"

        value_col2_x = info_x_start_value_col2
        draw.text((value_col2_x, info_y_start), high_price_text, font=font_normal, fill=text_color)
        draw.text((value_col2_x, info_y_start + line_height), volume_text, font=font_normal, fill=text_color)
        draw.text((value_col2_x, info_y_start + 2 * line_height), transaction_amount_text, font=font_normal, fill=text_color)


        # 6. Return the image as bytes
        img_byte_arr = io.BytesIO()
        new_image.save(img_byte_arr, format='PNG')
        img_byte_arr = io.BytesIO(img_byte_arr.getvalue())

        return chat.reply_media("IMAGE",[img_byte_arr])

    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None