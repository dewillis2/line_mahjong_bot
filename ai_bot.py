import os
import sys
from datetime import datetime
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import requests
from bs4 import BeautifulSoup
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


def get_tenhou_analysis_selenium(hand_str):
    """ 用 Selenium 解析天凤牌理分析 """
    print(f"【调试】启动 Selenium，解析手牌: {hand_str}")

    url = f"https://tenhou.net/2/?q={hand_str}"

    # 设置 Chrome 浏览器选项
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # 无界面模式
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    try:
        # 启动 Chrome 浏览器
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        print("【调试】Chrome WebDriver 启动成功")

        # 打开网页
        driver.get(url)
        print(f"【调试】打开网页: {url}")

        # 等待 JavaScript 加载
        time.sleep(3)

        # 获取完整 HTML
        html_content = driver.page_source
        print(f"【调试】网页 HTML 内容: {html_content[:500]}")  # 只打印前 500 个字符，避免输出太多

        driver.quit()  # 关闭浏览器
        print("【调试】Chrome WebDriver 关闭成功")

        # 解析 HTML
        soup = BeautifulSoup(html_content, "html.parser")

        # 查找 <pre> 标签（现在应该已经加载出来了）
        pre_tags = soup.find_all("pre")
        if pre_tags:
            print("【调试】成功找到 <pre> 标签")
            return pre_tags[-1].text.strip()

        # 如果没有 <pre>，尝试直接抓取文本
        text_content = soup.get_text()
        lines = [line.strip() for line in text_content.split("\n") if "打" in line]
        if lines:
            print("【调试】成功找到推荐切牌信息")
            return "\n".join(lines)

        return "解析失败，未找到分析结果。"

    except Exception as e:
        print(f"【错误】Selenium 执行失败: {e}")
        return f"【错误】Selenium 执行失败: {e}"



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
    elif text.startswith("牌理 "):
        hand_str = text.split("牌理 ")[-1].strip()
        analysis_result = get_tenhou_analysis_selenium(hand_str)
        res.append(TextMessage(text=f" 天凤分析结果：\n{analysis_result}"))
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
