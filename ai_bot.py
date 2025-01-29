import os
import sys
from datetime import datetime
import random
from email import message_from_string
import re
from pickle import FALSE

#計算
from mahjong.hand_calculating.hand import HandCalculator
#麻雀牌
from mahjong.tile import TilesConverter
#役, オプションルール
from mahjong.hand_calculating.hand_config import HandConfig, OptionalRules
#鳴き
from mahjong.meld import Meld
#風(場&自)
from mahjong.constants import EAST, SOUTH, WEST, NORTH
from flask import Flask, request, abort

from linebot.v3 import WebhookHandler

from linebot.v3.webhooks import MessageEvent, TextMessageContent, UserSource
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, TextMessage, ReplyMessageRequest, ImageMessage
from linebot.v3.exceptions import InvalidSignatureError

from openai import AzureOpenAI

mahjong_tiles = {
    "中": "https://i.imgur.com/NkvWJok.png",
    "發": "https://i.imgur.com/yZTmnmR.png",
    "白": "https://i.imgur.com/J6cDLqV.png",
    "東": "https://i.imgur.com/lTq2Rs9.png",
    "南": "https://i.imgur.com/3SJbe2s.png",
    "西": "https://i.imgur.com/lCp6CTE.png",
    "北": "https://i.imgur.com/mpb5P3t.png",
    "1m": "https://i.imgur.com/lA3XAl5.png",
    "2m": "https://i.imgur.com/chkqIc1.png",
    "3m": "https://i.imgur.com/ZmkaDyI.png",
    "4m": "https://i.imgur.com/EvbFGDe.png",
    "赤5m": "https://i.imgur.com/8vwfWav.png",
    "5m": "https://i.imgur.com/bZkPPAN.png",
    "6m": "https://i.imgur.com/SfDRtHH.png",
    "7m": "https://i.imgur.com/vA4Gq0x.png",
    "8m": "https://i.imgur.com/7UZyWEI.png",
    "9m": "https://i.imgur.com/RgFjRU9.png",
    "1s": "https://i.imgur.com/TSXFOpv.png",
    "2s": "https://i.imgur.com/l3p5XQX.png",
    "3s": "https://i.imgur.com/fjCAQeo.png",
    "4s": "https://i.imgur.com/188gvax.png",
    "赤5s": "https://i.imgur.com/BRJYbmX.png",
    "5s": "https://i.imgur.com/xxYMvdM.png",
    "6s": "https://i.imgur.com/hp8jLzT.png",
    "7s": "https://i.imgur.com/SxWWnAV.png",
    "8s": "https://i.imgur.com/TbvDaZP.png",
    "9s": "https://i.imgur.com/fZghtdB.png",
    "1p": "https://i.imgur.com/OFtRjYg.png",
    "2p": "https://i.imgur.com/hDyh0qA.png",
    "3p": "https://i.imgur.com/sToQuIR.png",
    "4p": "https://i.imgur.com/b0YwWwY.png",
    "赤5p": "https://i.imgur.com/10abXgD.png",
    "5p": "https://i.imgur.com/mrSWlbR.png",
    "6p": "https://i.imgur.com/fH0iz1a.png",
    "7p": "https://i.imgur.com/l1S8JAK.png",
    "8p": "https://i.imgur.com/25k8jBc.png",
    "9p": "https://i.imgur.com/2s1J9SL.png",
}

calculator = HandCalculator()  # 创建 HandCalculator 实例

config_mapping = {
    1: "is_riichi",
    2: "player_wind",
    3: "player_wind",
    4: "player_wind",
    5: "player_wind",
    6: "round_wind",
    7: "round_wind",
    8: "round_wind",
    9: "round_wind",
    10: "is_ippatsu",
    11: "is_rinshan",
    12: "is_chankan",
    13: "is_haitei",
    14: "is_houtei",
    15: "is_daburu_riichi",
    16: "is_nagashi_mangan",
    17: "is_tenhou",
    18: "is_renhou",
    19: "is_chiihou"
}

# **用户选择的值**
value_mapping = {
    2: "EAST", 3: "SOUTH", 4: "WEST", 5: "NORTH",
    6: "EAST", 7: "SOUTH", 8: "WEST", 9: "NORTH"
}

def print_hand_result(hand_result):
    # 翻数, 符数
    print(hand_result.han, hand_result.fu)
    # 点数(ツモアガリの場合[左：親失点, 右:子失点], ロンアガリの場合[左:放銃者失点, 右:0])
    print(hand_result.cost['main'], hand_result.cost['additional'])
    # 役
    print(hand_result.yaku)
    # 符数の詳細
    for fu_item in hand_result.fu_details:
        print(fu_item)
    print('')

def extract_first_part(message):
    """
    从输入消息中提取第一个逗号（，）之前的信息
    """
    parts = message.split(",")  # 按照第一个逗号分割
    return parts[0].strip()

def extract_2_commas(message):
    """
    提取第一个逗号和第二个逗号之间的内容
    """
    parts = message.split(",")  # 按中文逗号分割
    return parts[1].strip()  # 提取第2个部分（索引 1）

def extract_3_commas(message):
    """
    提取第二个和第三个逗号之间的内容
    """
    parts = message.split(",")  # 按英文逗号分割
    return parts[2].strip() if len(parts) > 3 else ""  # 提取索引 2（第三个部分）

def extract_4_commas(message):
    """
    提取第三个和第四个逗号之间的内容
    """
    parts = message.split(",")  # 按英文逗号分割
    return parts[3].strip() if len(parts) > 4 else ""  # 提取索引 3（第 4 段）

def extract_5_commas(message):
    """
    提取第四个逗号之后的内容
    """
    parts = message.split(",")  # 按英文逗号分割
    print(parts[4].strip())
    return parts[4].strip()

def extract_symbols_with_types(message):
    """
    提取所有 () [] {} :: 之间的内容，并标明符号类型
    """
    # 匹配所有符号及其内容
    pattern = r'\((.*?)\)|\[(.*?)\]|\{(.*?)\}|:(.*?):'
    matches = re.finditer(pattern, message)

    extracted_data = []

    for match in matches:
        if match.group(1):  # ()
            extracted_data.append(("()", match.group(1)))
        elif match.group(2):  # []
            extracted_data.append(("[]", match.group(2)))
        elif match.group(3):  # {}
            extracted_data.append(("{}", match.group(3)))
        elif match.group(4):  # ::
            extracted_data.append(("::", match.group(4)))

    return extracted_data

def extract_tiles(message):
    """
    提取麻将牌的数字和花色 (m, p, s) 并存入列表
    """
    matches = re.findall(r'(\d+)([mps])', message)  # 匹配 "数字 + 字母"

    tile_list = []
    for num, suit in matches:
        tile_list.append({"num": num, "suit": suit})  # 记录每张牌的信息

    return tile_list

def get_tiles(text):
    t = extract_first_part(text)
    man = get_man(t)
    pin = get_pin(t)
    sou = get_sou(t)
    honors = get_honors(t)
    tiles = TilesConverter.string_to_136_array(man=man, pin=pin, sou=sou, honors=honors)
    return tiles

def get_man(text):
    man = ''.join(re.findall(r'(\d+)m', text))  # 提取所有万子
    return man

def get_pin(text):
    pin = ''.join(re.findall(r'(\d+)p', text))
    return pin

def get_sou(text):
    sou = ''.join(re.findall(r'(\d+)s', text))
    return sou

def get_honors(text):
    honors = ''.join(re.findall(r'(\d+)z', text))
    return honors

def get_win(text):
    t = extract_2_commas(text)
    if t.endswith("m"):
        win_tile = TilesConverter.string_to_136_array(man=t[0])[0]
    elif t.endswith("p"):
        win_tile = TilesConverter.string_to_136_array(pin=t[0])[0]
    elif t.endswith("s"):
        win_tile = TilesConverter.string_to_136_array(sou=t[0])[0]
    elif t.endswith("z"):
        win_tile = TilesConverter.string_to_136_array(honors=t[0])[0]
    return win_tile

def get_melds(text):
    t = extract_3_commas(text)
    if t.strip() == "":  # 用户输入空格，表示没有鸣牌
        return None
    e = extract_symbols_with_types(t)
    melds=[]
    for symbol, content in e:
        if symbol == "()":
            if content.endswith("m"):
                m = Meld(Meld.CHI, TilesConverter.string_to_136_array(man=content[:-1]))
            if content.endswith("p"):
                m = Meld(Meld.CHI, TilesConverter.string_to_136_array(pin=content[:-1]))
            if content.endswith("s"):
                m = Meld(Meld.CHI, TilesConverter.string_to_136_array(sou=content[:-1]))
            if content.endswith("z"):
                m = Meld(Meld.CHI, TilesConverter.string_to_136_array(honors=content[:-1]))
        elif symbol == "[]":
            if content.endswith("m"):
                m = Meld(Meld.PON, TilesConverter.string_to_136_array(man=content[:-1]))
            if content.endswith("p"):
                m = Meld(Meld.PON, TilesConverter.string_to_136_array(pin=content[:-1]))
            if content.endswith("s"):
                m = Meld(Meld.PON, TilesConverter.string_to_136_array(sou=content[:-1]))
            if content.endswith("z"):
                m = Meld(Meld.PON, TilesConverter.string_to_136_array(honors=content[:-1]))
        elif symbol == "{}":
            if content.endswith("m"):
                m = Meld(Meld.KAN, TilesConverter.string_to_136_array(man=content[:-1]), False)
            if content.endswith("p"):
                m = Meld(Meld.KAN, TilesConverter.string_to_136_array(pin=content[:-1]), False)
            if content.endswith("s"):
                m = Meld(Meld.KAN, TilesConverter.string_to_136_array(sou=content[:-1]), False)
            if content.endswith("z"):
                m = Meld(Meld.KAN, TilesConverter.string_to_136_array(honors=content[:-1]), False)
        elif symbol == "::":
            if content.endswith("m"):
                m = Meld(Meld.KAN, TilesConverter.string_to_136_array(man=content[:-1]))
            if content.endswith("p"):
                m = Meld(Meld.KAN, TilesConverter.string_to_136_array(pin=content[:-1]))
            if content.endswith("s"):
                m = Meld(Meld.KAN, TilesConverter.string_to_136_array(sou=content[:-1]))
            if content.endswith("z"):
                m = Meld(Meld.KAN, TilesConverter.string_to_136_array(honors=content[:-1]))
        melds.append(m)
    return melds


def get_dora(text):
    t = extract_4_commas(text)
    print(f"DEBUG: 提取的 dora 数据 = '{t}'")  # 调试信息

    if t.strip() == "":  # 用户输入空格，表示没有宝牌
        print("DEBUG: dora 输入为空，返回 None")
        return None

    e = extract_tiles(t)
    print(f"DEBUG: 提取的 tile 数据 = {e}")  # 确保格式正确

    d_i = []
    for tile in e:
        num = tile["num"]
        if tile["suit"] == 'm':
            suit = "man"
        if tile["suit"] == 'p':
            suit = "pin"
        if tile["suit"] == 's':
            suit = "sou"
        if tile["suit"] == 'z':
            suit = "honor"
        tile_str = f"{num}{suit}"  # 组合完整的牌字符串，比如 '7p', '9s'

        # **转换为 136 编码**
        converted_tile = TilesConverter.string_to_136_array(**{suit: num})[0]
        d_i.append(converted_tile)
        print(f"DEBUG: 当前解析出的 dora = {converted_tile}")

    print(f"DEBUG: 最终 dora 指示牌 = {d_i}")
    return d_i


def get_config(text):
    t = extract_5_commas(text)
    if t.strip() == "":  # 如果用户输入为空，则返回默认 HandConfig
        return HandConfig()

    user_choices = set(map(int, t.split()))  # 解析用户输入
    config_params = {}

    # 遍历用户选择的数字，填充 HandConfig 参数
    for key in user_choices:
        if key in config_mapping:
            param_name = config_mapping[key]
            config_params[param_name] = value_mapping.get(key, True)  # 如果是风，填风位，否则填 True

    print(f"DEBUG: 生成的参数字典 = {config_params}")  # 确保数据正确
    config = HandConfig(**config_params)  # 创建 HandConfig
    print(f"DEBUG: config.__dict__ = {config.__dict__}")  # 确认 HandConfig 内部数据

    return config

def format_hand_result(hand_result):
    """
    格式化手牌计算结果，适用于 LINE 消息
    """
    # 翻数 & 符数
    result_text = f"【点数计算结果】\n翻数: {hand_result.han} 翻\n符数: {hand_result.fu} 符\n\n"

    # 点数信息（自摸 & 放铳）
    main_cost = hand_result.cost['main']
    additional_cost = hand_result.cost['additional']
    result_text += f"【点数】\n自摸: {main_cost}（子:{additional_cost}）\n放铳: {main_cost}\n\n"

    # 役种
    result_text += "【役】\n"
    result_text += ", ".join(hand_result.yaku) + "\n\n"

    # 符的详细信息
    result_text += "【符详细】\n"
    for fu_item in hand_result.fu_details:
        result_text += f"- {fu_item}\n"

    return result_text.strip()  # 去掉多余空行


# get LINE credentials from environment variables
channel_access_token = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
channel_secret = os.environ["LINE_CHANNEL_SECRET"]

if channel_access_token is None or channel_secret is None:
    print("Specify LINE_CHANNEL_ACCESS_TOKEN and LINE_CHANNEL_SECRET as environment variable.")
    sys.exit(1)

# get Azure OpenAI credentials from environment variables
azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
azure_openai_api_key = os.getenv("AZURE_OPENAI_API_KEY")
azure_openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION")
azure_openai_model = os.getenv("AZURE_OPENAI_MODEL")

if azure_openai_endpoint is None or azure_openai_api_key is None or azure_openai_api_version is None:
    raise Exception(
        "Please set the environment variables AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, and AZURE_OPENAI_API_VERSION."
    )


handler = WebhookHandler(channel_secret)
configuration = Configuration(access_token=channel_access_token)

app = Flask(__name__)
ai = AzureOpenAI(
    azure_endpoint=azure_openai_endpoint, api_key=azure_openai_api_key, api_version=azure_openai_api_version
)


# LINEボットからのリクエストを受け取るエンドポイント
@app.route("/callback", methods=["POST"])
def callback():
    # get X-Line-Signature header value
    signature = request.headers["X-Line-Signature"]

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError as e:
        abort(400, e)

    return "OK"


chat_history = []


# 　AIへのメッセージを初期化する関数
def init_chat_history():
    chat_history.clear()
    system_role = {
        "role": "system",
        "content": [
            {
                "type": "text",
                "text": "あなたは創造的思考の持ち主です。話し方は関西弁でおっさん口調，ハイテンションで絵文字を使います。専門は金融アナリストで，何かにつけて自分の専門とこじつけて説明します。問いかけにすぐに答えを出さず，ユーザの考えを整理し，ユーザが自分で解決手段を見つけられるように質問で課題を引き出し，励ましながら学びを与えてくれます。",
            },
        ],
    }
    chat_history.append(system_role)


# 　返信メッセージをAIから取得する関数
def get_ai_response(from_user, text):
    # ユーザのメッセージを記録
    user_msg = {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": text,
            },
        ],
    }
    chat_history.append(user_msg)

    # AIのパラメータ
    parameters = {
        "model": azure_openai_model,  # AIモデル
        "max_tokens": 100,  # 返信メッセージの最大トークン数
        "temperature": 0.5,  # 生成の多様性（0: 最も確実な回答、1: 最も多様な回答）
        "frequency_penalty": 0,  # 同じ単語を繰り返す頻度（0: 小さい）
        "presence_penalty": 0,  # すでに生成した単語を再度生成する頻度（0: 小さい）
        "stop": ["\n"],
        "stream": False,
    }

    # AIから返信を取得
    ai_response = ai.chat.completions.create(messages=chat_history, **parameters)
    res_text = ai_response.choices[0].message.content

    # AIの返信を記録
    ai_msg = {
        "role": "assistant",
        "content": [
            {"type": "text", "text": res_text},
        ],
    }
    chat_history.append(ai_msg)
    return res_text

def generate_fortune():
    """ 随机抽取一张幸运麻将牌 """
    tile, image_url = random.choice(list(mahjong_tiles.items()))
    return tile, image_url

# 　返信メッセージを生成する関数
def generate_response(from_user, text):
    res = []
    if text in ["今日のラッキー牌", "麻雀占い", "占い"]:
        # 生成幸运牌
        tile, image_url = generate_fortune()
        res.append(TextMessage(text=f"{from_user}さん、今日のラッキー牌は…「{tile}」です！"))
        res.append(ImageMessage(original_content_url=image_url, preview_image_url=image_url))
    elif text.startswith("点数計算 "):  # 确保用户输入是 点数計算 + 牌
        hand_input = text[len("点数計算 "):].strip()  # 提取 "点数計算 " 之后的部分
        t = get_tiles(hand_input)
        w = get_win(hand_input)
        m = get_melds(hand_input)
        d = get_dora(hand_input)
        c = get_config(hand_input)
        print("DEBUG: tiles =", t)
        print("DEBUG: win_tile =", w)
        print("DEBUG: melds =", m)
        print("DEBUG: dora =", d)
        print("DEBUG: config =", c)

        result = calculator.estimate_hand_value(t, w, m, d, c)
        res.append(TextMessage(text=f"【点数計算結果】\n翻数: {result.han} 翻\n符数: {result.fu} 符"))

        main_cost = result.cost['main']
        additional_cost = result.cost['additional']
        res.append(TextMessage(text=f"【点数】\nツモ: {main_cost}（子: {additional_cost}）\nロン: {main_cost}"))


        if result.yaku:
            yaku_text = "【役】\n" + ", ".join(str(yaku) for yaku in result.yaku)
            res.append(TextMessage(text=yaku_text))
        else:
            res.append(TextMessage(text="【役】\n役なし"))

        if result.fu_details:
            fu_text = "【符詳細】\n" + "\n".join(f"- {fu}" for fu in result.fu_details)
            res.append(TextMessage(text=fu_text))
    else:
        # AIを使って返信を生成
        res = [TextMessage(text=get_ai_response(from_user, text))]
    return res


# メッセージを受け取った時の処理
@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    # 送られてきたメッセージを取得
    text = event.message.text

    # 返信メッセージの送信
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        res = []
        if isinstance(event.source, UserSource):
            # ユーザー情報が取得できた場合
            profile = line_bot_api.get_profile(event.source.user_id)
            # 返信メッセージを生成
            res = generate_response(profile.display_name, text)
        else:
            # ユーザー情報が取得できなかった場合
            # fmt: off
            # 定型文の返信メッセージ
            res = [
                TextMessage(text="ユーザー情報を取得できませんでした。"),
                TextMessage(text=f"メッセージ：{text}")
            ]
            # fmt: on

        # メッセージを送信
        line_bot_api.reply_message_with_http_info(ReplyMessageRequest(reply_token=event.reply_token, messages=res))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
