import requests
import datetime
import pytz
from iris import ChatContext, PyKV

all_url = "https://api.upbit.com/v1/market/all"
base_url = "https://api.upbit.com/v1/ticker?markets="
currency_url = "https://m.search.naver.com/p/csearch/content/qapirender.nhn?key=calculator&pkid=141&q=%ED%99%98%EC%9C%A8&where=m&u1=keb&u6=standardUnit&u7=0&u3=USD&u4=KRW&u8=down&u2=1"
binance_url = "https://api.binance.com/api/v3/ticker/"

def get_coin_info(chat: ChatContext):
    match chat.message.command:
        case "!코인":
            if chat.message.has_param:
                get_upbit(chat)
            else:
                get_upbit_all(chat)
        case "!내코인":
            get_my_coins(chat)
        case "!바낸":
            get_binance(chat)
        case "!김프":
            get_kimchi_premium(chat)
        case "!달러":
            usd_to_krw(chat)
        case "!코인등록":
            coin_add(chat)
        case "!코인삭제":
            coin_remove(chat)

def get_upbit(chat: ChatContext):
    kv = PyKV()
    query = chat.message.param.upper()
    res = requests.get(base_url + 'KRW-' + query)
    if 'error' in res.text:
        try:
            result_json, query = get_upbit_korean(query)
        except:
            chat.reply("검색된 코인이 없습니다.")
            return None

    else:
        result_json = res.json()[0]
    
    price = result_json['trade_price']
    change = result_json['signed_change_rate']*100
    
    if price % 1 == 0:
        price = int(price)
    
    result = query + f'\n현재가 : {price:,}원\n등락률 : {change:,.2f}%'
    
    user_coin_info = kv.get(f"coin.{str(chat.sender.id)}")[query]

    if user_coin_info:
        amount = user_coin_info["amount"]
        average = user_coin_info["average"]
        seed = average*amount
        total = round(result_json['trade_price']*amount,0)
        percent = round((total/seed-1)*100,1)
        plus_mark = "+" if percent > 0 else ""
        result += f'\n총평가금액 : {total:,.0f}원({plus_mark}{percent:,.1f}%)\n총매수금액 : {seed:,.0f}원\n보유수량 : {amount:,.0f}개\n평균단가 : {average:,}원'

    chat.reply(result)

def get_my_coins(chat: ChatContext):
    kv = PyKV()
    my_coins = kv.get(f"coin.{str(chat.sender.id)}")
    if not my_coins:
        chat.reply("등록된 코인이 없습니다. !코인등록 기능으로 코인을 등록하세요.")
        return None

    my_coins_list = []
    for key in my_coins.keys():
        my_coins_list.append("KRW-" + key)
    
    coins_query = ",".join(my_coins_list)
    
    res = requests.get(base_url + coins_query)
    
    result_list = []
    coins = {}
    current_total = 0
    bought_total = 0
    
    for coin in res.json():
        coins[coin['market'][4:]] = {'price' : coin['trade_price'], 'change' : coin['signed_change_rate']*100}
    
    for key in coins.keys():
        to_append = f'{key}\n현재가 : {coins[key]["price"]} 원\n등락률 : {coins[key]["change"]:.2f} %'
        amount = my_coins[key]["amount"]
        average = my_coins[key]["average"]
        seed = average*amount
        total = round(coins[key]["price"]*amount,0)
        percent = round((total/seed-1)*100,1)
        plus_mark = "+" if percent > 0 else ""
        to_append = to_append + f'\n총평가금액 : {total:,.0f}원({plus_mark}{percent:,.1f}%)\n총매수금액 : {seed:,.0f}원\n보유수량 : {amount:,.0f}개\n평균단가 : {average:,}원'
        result_list.append(to_append)
        current_total += total
        bought_total += seed
    result = '\n\n'.join(result_list)
    total_change = round((current_total/bought_total-1)*100,1)
    result = '내 코인\n' + '\u200b'*500 + f'\n전체\n총평가 : {current_total:,.0f}원\n총매수 : {bought_total:,.0f}원\n평가손익 : {current_total-bought_total:+,.0f}원\n수익률 : {total_change:+,.1f}%\n\n' + result
    
    chat.reply(result)
    
def get_upbit_all(chat: ChatContext):
    res = requests.get(all_url)
    krw_coins = []
    for market in res.json():
        if 'KRW' in market['market']:
            krw_coins.append(market['market'])

    res = requests.get(base_url + ','.join(krw_coins))
    
    result_list = []
    coins = {}
    result_list.append('업비트 원화시세\n' + '\u200b'*500)

    for coin in res.json():
        coins[coin['market'][4:]] = {'price' : coin['trade_price'], 'change' : coin['signed_change_rate']*100}
    coin_list = sorted(coins.items(),key = lambda x: x[1]['change'],reverse=True)
    
    for item in coin_list:
        to_append = f'{item[0]}\n현재가 : {item[1]["price"]} 원\n등락률 : {item[1]["change"]:.2f} %'
        result_list.append(to_append)
    result = '\n\n'.join(result_list)
    
    chat.reply(result)

def get_upbit_korean(query):
    res_eng_query = requests.get(all_url)
    for market in res_eng_query.json():
        if 'KRW' in market['market'] and query in market['korean_name']:
            eng_query = market['market']
            if query == market['korean_name']:
                break

    res = requests.get(base_url + eng_query)
    return (res.json()[0],eng_query[4:])


def get_binance(chat: ChatContext):
    try:
        query = chat.message.param.upper()
        query_split = query.split("/")
        query = "".join(query_split)
        currency = get_USDKRW()
        r = requests.get(binance_url+'24hr').json()
        is_USDT = query_split[1] in ["USDT", "BUSD", "USDC"]
        for coin in r:
            if coin['symbol'] == 'BTCUSDT':
                BTCUSDT = float(coin['lastPrice'])
                if query == 'BTCUSDT':
                    price = BTCUSDT
                    change = float(coin['priceChangePercent'])
            elif coin['symbol'] == query:
                price = float(coin['lastPrice'])
                change = float(coin['priceChangePercent'])
            elif coin['symbol'] == query_split[1]+'USDT':
                to_USDT = float(coin['lastPrice'])
        if not is_USDT:
            price = price*to_USDT
        BTCKRW = requests.get(base_url + "KRW-BTC").json()[0]["trade_price"]
        query_KRW = price*currency
        query_KRW_kimp = (BTCKRW/(BTCUSDT*currency))*query_KRW
        res = f'{query}\nUSD : ${price:,f}\nKRW : ￦{query_KRW:,.2f}\nKRW(김프) : ￦{query_KRW_kimp:,.2f}\n등락률 : {change:+.2f}%\n환율 : ￦{currency:,.0f}'
        chat.reply(res)
    except Exception as e:
        print(e)
        chat.reply('코인이 정확하지 않거나 오류가 발생하였습니다. 코인심볼과 화폐단위를 함께 적어주세요. 예시 : BTC/USDT, ETC/USDT, IQ/BNB')

def get_kimchi_premium(chat: ChatContext):
    BTCUSDT = float(requests.get(binance_url+"price?symbol=BTCUSDT").json()["price"])
    BTCKRW = requests.get(base_url + "KRW-BTC").json()[0]["trade_price"]
    USDKRW = get_USDKRW()
    local_time = datetime.datetime.now()
    eastern = pytz.timezone('US/Eastern')
    eastern_time = local_time.astimezone(eastern)
    EST = eastern_time.strftime("%d일 %H시%M분")
    BTCUSDT_to_KRW = BTCUSDT*USDKRW
    BTCKRW_to_USDT = BTCKRW/USDKRW
    kimchi_premium = (BTCKRW - BTCUSDT_to_KRW) / BTCUSDT_to_KRW * 100

    chat.reply(f'김치 프리미엄\n업빗 : ￦{BTCKRW:,.0f}(${BTCKRW_to_USDT:,.0f})\n바낸 : ￦{BTCUSDT_to_KRW:,.0f}(${BTCUSDT:,.0f})\n김프 : {kimchi_premium:.2f}%\n환율 : ￦{USDKRW:,.0f}\n버거시간(동부) : {EST}')

def usd_to_krw(chat: ChatContext):
    usd = float(chat.message.param)
    USDKRW = get_USDKRW()
    chat.reply(f'${usd:,.2f} = {USDKRW*float(chat.message.msg[4:]):,.2f}원\n환율 : {USDKRW:,.2f}원')

def get_USDKRW():
    USDKRW = float(requests.get(currency_url).json()["country"][1]["value"].replace(",",""))
    return USDKRW

def coin_add(chat: ChatContext):
    msg_split = chat.message.msg.split(" ")
    if not len(msg_split) == 4:
        chat.reply('"!코인등록 코인명(영문심볼) 보유수량 평균단가"로 입력하세요.')
        return None
    symbol = msg_split[1].upper()
    amount = float(msg_split[2].replace(',',''))
    average = float(msg_split[3].replace(',',''))
    r = requests.get(base_url + 'KRW-' + symbol)
    if 'error' in r.text:
        chat.reply('업비트 원화마켓만 지원합니다.\n"!코인등록 코인명(영문심볼) 보유수량 평균단가"로 입력하세요.')
        return None

    kv = PyKV()
    user_kv = kv.get(f"coin.{str(chat.sender.id)}")
    if not user_kv:
        user_kv = {}
    
    user_kv[symbol] = {"amount":amount, "average":average}
    kv.put(f"coin.{str(chat.sender.id)}",user_kv)

    chat.reply(f'{symbol}코인을 {average}원에 {amount}개 등록하였습니다.')

def coin_remove(chat: ChatContext):
    kv = PyKV()
    msg_split = chat.message.msg.split(" ")
    if not len(msg_split) == 2:
        chat.reply('"!코인삭제 코인명(영문심볼)"으로 입력하세요.')
        return None
    
    symbol = msg_split[1].upper()
    
    user_kv = kv.get(f"coin.{str(chat.sender.id)}")
    if not user_kv:
        user_kv = {}
    
    if symbol in user_kv.keys():
        user_kv.pop(symbol)
        kv.put(f"coin.{str(chat.sender.id)}", user_kv)
        chat.reply(f'{symbol}코인을 삭제하였습니다.')
    else:
        chat.reply('코인이 없거나 잘못된 명령입니다.\n"!코인삭제 코인명(영문심볼)"으로 입력하세요.')