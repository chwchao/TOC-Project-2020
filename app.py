import os
import sys

from flask import Flask, jsonify, request, abort, send_file
from dotenv import load_dotenv
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageSendMessage
import pymongo

from fsm import TocMachine
from utils import send_text_message

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
import time
import datetime

chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--remote-debugging-port=9222')
chrome_options.add_argument('--headless')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--no-sandbox')
chrome_options.binary_location = os.getenv("GOOGLE_CHROME_BIN", None)
browser = webdriver.Chrome(executable_path=chrome_driver_path, chrome_options=chrome_options)
load_dotenv()

machine = TocMachine(
    states=[
        "visitor", "user", "naming", "add_course", "delete_course"
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
            "trigger": "go_to_naming",
            "source": "user",
            "dest": "naming",
            "conditions": "go_to_naming"
        },
        {
            "trigger": "rename",
            "source": "naming",
            "dest": "user",
            "conditions": "rename",
        },
        {
            "trigger": "logout",
            "source": "user",
            "dest": "visitor",
            "conditions": "logout"
        },
        {
            "trigger": "go_to_add_course",
            "source": "user",
            "dest": "add_course",
            "conditions": "go_to_add_course"
        },
        {
            "trigger": "add_course",
            "source": "add_course",
            "dest": "user",
            "conditions": "add_course"
        }, 
        {
            "trigger": "go_to_delete_course",
            "source": "user",
            "dest": "delete_course",
            "conditions": "go_to_delete_course"
        },
        {
            "trigger": "delete_course",
            "source": "delete_course",
            "dest": "user",
            "conditions": "delete_course"
        },
        {
            "trigger": "cancel",
            "source": ["add_course", "delete_course"],
            "dest": "user",
            "conditions": "cancel"
        }
    ],
    initial="visitor",
    auto_transitions=False,
    show_conditions=True
)

app = Flask(__name__, static_url_path="/public")

# get channel_secret and channel_access_token from your environment variable
channel_secret = os.getenv("LINE_CHANNEL_SECRET", None)
channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", None)
mongo_uri = os.getenv("MONGODB_URI", None)
chrome_driver_path = os.getenv("CHROMEDRIVER_PATH", None)
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
db = client["heroku_46z74r0d"]
coll_user = db.user


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
    body = request.get_data(as_text=True)
    app.logger.info(f"Request body: {body}")

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
            user = coll_user.find_one({"id":event.source.user_id})
            return user
        
        user = get_user(event)
        print(user)
        user_state = ""
        if user == None:
            user_state = "visitor"
        else:
            user_state = user["state"]
        machine.set_start(user_state)

        if event.message.text.lower() == "logout":
            if user_state != "visitor":
                machine.logout(event)
                send_text_message(event.reply_token, "Bye " + user["name"])
                continue
            else:
                send_text_message(event.reply_token, "Please login first")
                continue

        # visitor
        if user_state == "visitor":
            if event.message.text.lower() == "login":
                exist = machine.login(event)
                if exist == True:
                    send_text_message(event.reply_token, "Hello " + user["name"])
                else:
                    machine.register()
                    send_text_message(event.reply_token, "Please enter your name:")
            else:
                send_text_message(event.reply_token, "Please login first")

        # user (opts)
        elif user_state == "user":
            if event.message.text.lower() == "rename":
                machine.go_to_naming(event)
                send_text_message(event.reply_token, "Please enter your name:")
            elif event.message.text.lower() == "add":
                machine.go_to_add_course(event)
                send_text_message(event.reply_token, "Please enter course number:")
            elif event.message.text.lower() == "delete":
                machine.go_to_delete_course(event)
                send_text_message(event.reply_token, "Please enter course number:")
            elif event.message.text.lower() == "list":
                if len(user["target"]) == 0:
                    send_text_message(event.reply_token, "You haven't follow any couse")
                else:
                    courses = ""
                    for course in user["target"]:
                        courses = courses + course
                        if course != user["target"][len(user["target"]) - 1]:
                            courses = course + "\n"
                    send_text_message(event.reply_token, courses)
            elif event.message.text.lower() == "check":

                def get_left(course):
                    department = course[0] +course[1]
                    course = course[2] + course[3] + course[4]
                    browser.get('http://course-query.acad.ncku.edu.tw/qry/qry001.php?dept_no=' + department)
                    count = 1
                    while 1:
                        if browser.find_element_by_xpath("//tr[" + str(count) + "]//td[3]").text == course:
                            break
                        count = count + 1
                    return browser.find_element_by_xpath("//tr[" + str(count) + "]//td[17]").text

                if len(user["target"]) == 0:
                    send_text_message(event.reply_token, "You haven't follow any couse")
                else:
                    courses = ""
                    for course in user["target"]:
                        courses = courses + course + " : " + get_left(course)
                        if course != user["target"][len(user["target"]) - 1]:
                            courses = courses + "\n"
                    send_text_message(event.reply_token, courses)
            elif event.message.text.lower() == "show fsm":
                message = ImageSendMessage(
                    original_content_url='https://1a6ca2ef.ngrok.io/fsm.png',
                    preview_image_url='https://1a6ca2ef.ngrok.io/fsm.png'
                )
                line_bot_api.reply_message(event.reply_token, message)

        # naming
        elif user_state == "naming":
            response = machine.rename(event, event.message.text)
            if response == True:
                send_text_message(event.reply_token, "Hello " + event.message.text)
            else:
                send_text_message(event.reply_token, "Rename failed, please try again.")

        # add course
        elif user_state == "add_course":
            if event.message.text.lower() == "cancel" :
                send_text_message(event.reply_token, "Canceled")
                machine.cancel(event)
            else:
                response = machine.add_course(event, event.message.text)
                if response == True:
                    send_text_message(event.reply_token, event.message.text + " added")
                else:
                    send_text_message(event.reply_token, "Please try again")

        # delete course
        elif user_state == "delete_course":
            if event.message.text.lower() == "cancel" :
                send_text_message(event.reply_token, "Canceled")
                machine.cancel(event)
            else:
                response = machine.delete_course(event, event.message.text)
                if response == True:
                    send_text_message(event.reply_token, event.message.text + " deleted")
                else:
                    send_text_message(event.reply_token, "Not exist or wrong format. Please try again")
                


    return "OK"


@app.route("/show-fsm", methods=["GET"])
def show_fsm():
    machine.get_graph().draw("fsm.png", prog="dot", format="png")
    return send_file("fsm.png", mimetype="image/png")


if __name__ == "__main__":
    port = os.environ.get("PORT", 8000)
    app.run(host="0.0.0.0", port=port, debug=True)
