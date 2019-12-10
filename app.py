import os
import sys

from flask import Flask, jsonify, request, abort, send_file
from dotenv import load_dotenv
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import pymongo

from fsm import TocMachine
from utils import send_text_message

load_dotenv()

machine = TocMachine(
    states=[
        "visitor", "user", "naming"
       # "course_add", "course_add_success", "course_add_failed"
       # "course_delete", "course_delete_success", "course_delete_failed",
       # "left_check"
        ],
    transitions=[
        {
            "trigger": "login",
            "source": "visitor",
            "dest": "user",
            "conditions": "login",
        },
        {
            "trigger": "register",
            "source": "visitor",
            "dest": "naming"
        },
        {
            "trigger": "has_name",
            "source": "check_name",
            "dest": "user"
        },
        {
            "trigger": "rename",
            "source": "naming",
            "dest": "user",
            "conditions": "rename",
        },
        {
            "trigger": "logout",
            "source": ["visitor", "user", "check_name", "naming"],
            "dest": "visitor",
            "conditions": "logout",
        },
        {
            "trigger": "state_check",
            "source": ["visitor", "user"],
            "dest": ["visitor", "user"],
            "conditions": "state_check",
        },
        {"trigger": "go_back", "source": ["state1", "state2"], "dest": "user"},
    ],
    initial="visitor",
    auto_transitions=False,
    show_conditions=True,
)

app = Flask(__name__, static_url_path="")


# get channel_secret and channel_access_token from your environment variable
channel_secret = os.getenv("LINE_CHANNEL_SECRET", None)
channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", None)
mongo_uri = os.getenv("MONGODB_URI", None)
if channel_secret is None:
    print("Specify LINE_CHANNEL_SECRET as environment variable.")
    sys.exit(1)
if channel_access_token is None:
    print("Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.")
    sys.exit(1)
if mongo_uri is None:
    print("Specify MONDODB_URI as environment variable.")
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
parser = WebhookParser(channel_secret)
client = pymongo.MongoClient(mongo_uri)
coll_user = client.user


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # parse webhook body
    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        abort(400)

    # if event is MessageEvent and message is TextMessage, then echo text
    for event in events:
        if not isinstance(event, MessageEvent):
            continue
        if not isinstance(event.message, TextMessage):
            continue

        line_bot_api.reply_message(
            event.reply_token, TextSendMessage(text=event.message.text)
        )

    return "OK"


@app.route("/webhook", methods=["POST"])
def webhook_handler():
    signature = request.headers["X-Line-Signature"]
    # get request body as text
    # body = request.get_data(as_text=True)
    # app.logger.info(f"Request body: {body}")

    # parse webhook body
    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        abort(400)

    # if event is MessageEvent and message is TextMessage, then echo text
    for event in events:
        if not isinstance(event, MessageEvent):
            continue
        if not isinstance(event.message, TextMessage):
            continue
        if not isinstance(event.message.text, str):
            continue
        print(f"\nFSM STATE: {machine.state}")
        print(f"REQUEST BODY: \n{body}")

        def get_user(event):
            user = coll_user.find_one({"id":event.userID})
            return user
        user = get_user(event)
        user_state = ""
        if user == None:
            user_state = "visitor"
        else:
            user_state = user.state
        machine.set_start(user_state)

        if user_state == "visitor":
            exist = machine.login(event)
            if exist == True:
                send_text_message(event.reply_token, "Login success!!")
            else:
                machine.register()

            

        
        
            
        
        response = machine.advance(event)
        if response == False:
            send_text_message(event.reply_token, "Not Entering any State")

    return "OK"


@app.route("/show-fsm", methods=["GET"])
def show_fsm():
    machine.get_graph().draw("fsm.png", prog="dot", format="png")
    return send_file("fsm.png", mimetype="image/png")


if __name__ == "__main__":
    port = os.environ.get("PORT", 8000)
    app.run(host="0.0.0.0", port=port, debug=True)
