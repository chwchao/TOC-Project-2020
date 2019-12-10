from transitions.extensions import GraphMachine
import os
from utils import send_text_message

import pymongo
mongo_uri = os.getenv("MONGODB_URI", None)
client = pymongo.MongoClient(mongo_uri)
db = client.heroku_46z74r0d
coll_user = db.user


class TocMachine(GraphMachine):
    def __init__(self, **machine_configs):
        self.machine = GraphMachine(model=self, **machine_configs)

    def login(self, event):
        user = coll_user.find_one({"id":event.source.user_id})
        if user == None:
            newUser = {
                "id" : event.source.user_id,
                "name" : "",
                "target" : [],
                "state" : "naming"
            }
            coll_user.insert_one(newUser)
            return False
        else:
            user["state"] = "user"
            coll_user.update_one({"id":event.source.user_id}, {'$set': user})
            return True

    def rename(self, event, name):
        user = coll_user.find_one({"id":event.source.user_id})
        user["state"] = "user"
        user["name"] = name
        coll_user.update_one({"id":event.source.user_id}, {'$set': user})
        return True

    def logout(self, event):
        user = coll_user.find_one({"id":event.source.user_id})
        user["state"] = "visitor"
        coll_user.update_one({"id":event.source.user_id}, {'$set': user})
        return True

    def go_to_naming(self, event):
        user = coll_user.find_one({"id":event.source.user_id})
        user["state"] = "naming"
        coll_user.update_one({"id":event.source.user_id}, {'$set': user})
        return True

    def go_to_add_course(self, event):
        user = coll_user.find_one({"id":event.source.user_id})
        user["state"] = "add_course"
        coll_user.update_one({"id":event.source.user_id}, {'$set': user})
        return True

    def add_course(self, event, course):
        if len(course) != 5 and course[0].isalpha() and course[1].isnumeric() and course[2].isnumeric() and course[3].isnumeric() and course[4].isnumeric():
            return False
        else:
            user = coll_user.find_one({"id":event.source.user_id})
            if course in user["target"]:
                return False
            else:
                user["state"] = "user"
                user["target"].append(course)
                coll_user.update_one({"id":event.source.user_id}, {'$set': user})
                return True

    def go_to_delete_course(self, event):
        user = coll_user.find_one({"id":event.source.user_id})
        user["state"] = "delete_course"
        coll_user.update_one({"id":event.source.user_id}, {'$set': user})
        return True

    def delete_course(self, event, course):
        if len(course) != 5 and course[0].isalpha() and course[1].isnumeric() and course[2].isnumeric() and course[3].isnumeric() and course[4].isnumeric():
            return False
        else:
            user = coll_user.find_one({"id":event.source.user_id})
            if course in user["target"]:
                user["target"].remove(course)
                user["state"] = "user"
                coll_user.update_one({"id":event.source.user_id}, {'$set': user})
                return True
            else:
                return False

    def cancel(self, event):
        user = coll_user.find_one({"id":event.source.user_id})
        user["state"] = "user"
        coll_user.update_one({"id":event.source.user_id}, {'$set': user})
        return True

    def set_start(self, state):
        self.startState = state
