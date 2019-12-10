from transitions.extensions import GraphMachine

from utils import send_text_message

class TocMachine(GraphMachine):
    def __init__(self, **machine_configs):
        self.machine = GraphMachine(model=self, **machine_configs)

    def login(self, event):
        user = coll_user.find_one({"id":event.userID})
        if user == None:
            newUser = {
                "id" : event.userID,
                "name" : "",
                "target" : [],
                "state" : "naming"
            }
            coll_user.insert_one(newUser)
            return False
        else:
            user.state = "user"
            result = collection.update_one({"id":event.userID}, {'$set': user})
            return True

    def rename(self, name):
        user = coll_user.find_one({"id":event.userID})
        user.state = "user"
        user.name = name
        result = collection.update_one({"id":event.userID}, {'$set': user})
        return True

    def set_start(self, state):
        self.startState = state

    def logout(self, event):
        return True

    def is_going_to_state1(self, event):
        text = event.message.text
        return text.lower() == "go to state1"

    def is_going_to_state2(self, event):
        text = event.message.text
        return text.lower() == "go to state2"

    def on_enter_state1(self, event):
        print("I'm entering state1")

        reply_token = event.reply_token
        send_text_message(reply_token, "Trigger state1")
        self.go_back()

    def on_exit_state1(self):
        print("Leaving state1")

    def on_enter_state2(self, event):
        print("I'm entering state2")

        reply_token = event.reply_token
        send_text_message(reply_token, "Trigger state2")
        self.go_back()

    def on_exit_state2(self):
        print("Leaving state2")
