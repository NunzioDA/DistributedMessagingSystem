import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from communication_API.consts import USER_INFO_PATH
from communication_API.server_API import get_chat_range, get_version
from dms_secure.hashing import hash_to_range
from dms_secure.signature_management import verify_signature
from model.message import Message


class MessageManager:
    def __init__(self,INBOX_DATA_PATH, my_address, my_username="", SENT_PATH = "", ):
        self.INBOX_DATA_PATH = INBOX_DATA_PATH
        self.my_username = my_username
        self.SENT_PATH = SENT_PATH
        self.my_address = my_address

    def get_file_path(self, sender, receiver):
        if(sender == self.my_username):
            path = self.SENT_PATH
            file_path = path + receiver + ".json"
        else:
            path = self.INBOX_DATA_PATH + receiver + "/"
            file_path = path + sender + ".json"

        return path, file_path

    def save_message(self, message : Message):     

        path, file_path = self.get_file_path(message.username, message.receiver_username)

        saved = False

        chat = self.get_chat(message.username, message.receiver_username)

        if(not os.path.exists(path)):
            os.makedirs(path)

        with open(file_path, 'w') as in_box_file:
            json_message = {
                "signature": message.signature,
                "text" : message.text,
                "date_time" : message.time,
                "receiver_key": message.receiver_key,
                "sender_key": message.sender_key,
                "key_signature": message.key_signature
            }

            message_datetime = datetime.strptime(message.time,"%Y-%m-%d %H:%M:%S.%f%z")
            if(len(chat["income_chat"])>0):
                for i in range(len(chat["income_chat"])- 1,-1,-1):
                    old_datetime = datetime.strptime(chat["income_chat"][i]["date_time"],"%Y-%m-%d %H:%M:%S.%f%z")
                    if(old_datetime <= message_datetime):
                        if(message_datetime != old_datetime or 
                           message.text != chat["income_chat"][i]["text"]):
                            chat["income_chat"].insert(i + 1, json_message)
                            saved = True
                        break
            else:
                chat["income_chat"].append(json_message)
                saved = True
            json.dump(chat, in_box_file) 
        return saved
    
    def _update_chat(self, sender, receiver, servers, messages_queue_lock, messages_queue, verify_message=lambda x:x):

        most_uptodate_server_address = 0
        latest_version = 0
        latest_hash = ""
        found_something = False

        for server in servers:
            if(server != self.my_address):
                try:
                    response = get_version(server, sender, receiver, self.my_address)
                except Exception as e:
                    response = "{\"hash\": 0, version: 0}"
                    
                if(response != False):
                    response = json.loads(response)


                    if(response["version"]>latest_version):
                        most_uptodate_server_address = server
                        latest_version = response["version"]
                        latest_hash = response["hash"]


        try:

            if(most_uptodate_server_address != 0):
                hash_chat, version = self._get_version(sender, receiver)

                if(version < latest_version or (version == latest_version and hash_chat != latest_hash)):
                    income_chat = self.get_chat(sender,receiver)["income_chat"]

                    for index in range(len(income_chat), -1, -1):
                        if(len(income_chat)<latest_version):
                            if(index-1 >= 0):
                                start_message = Message(
                                    sender,
                                    receiver,
                                    "",
                                    "",
                                    income_chat[index-1]["date_time"],
                                    urgent=0
                                ) 
                            else:
                                start_message = None


                            if(index < len(income_chat)):
                                end_message = Message(
                                    sender,
                                    receiver,
                                    "",
                                    "",
                                    income_chat[index]["date_time"],
                                    urgent=0
                                ) 
                            else:
                                end_message = Message(
                                    sender,
                                    receiver,
                                    "",
                                    "",
                                    str(datetime.now(timezone.utc)),
                                    urgent=0
                                )

                            income_update = json.loads(get_chat_range(int(most_uptodate_server_address), start_message, end_message, self.my_address))
                            income_update_to_msgs = []

                            for income_msg in income_update:
                                update_message = self._create_message_from_chat(sender, receiver, income_msg)
                                verify_message(update_message)# Controlli aggiuntivi per i messaggi
                                self.verify_message(update_message)
                                update_message.notifiable = False                                
                                income_update_to_msgs.append(update_message)  

                            
                            if(len(income_update_to_msgs) > 0):
                                income_update_to_msgs[-1].notify_update_listener = True
                                found_something = True

                            income_chat[index:index] = income_update

                            messages_queue_lock.acquire()
                            messages_queue[0:0] = income_update_to_msgs
                            messages_queue_lock.release()
                        else:
                            break
                        
        except Exception as e:
            print("ERRORE:"+ str(e))

        return found_something

    def _create_message_from_chat(self, sender, receiver, message):
        return Message(
            sender,
            receiver,
            message["signature"],
            message["text"],
            message["date_time"],
            message["receiver_key"],
            message["sender_key"],
            message["key_signature"],
            0,
            "",
            0
        )

    def _get_version(self, sender, receiver):
        income_chat = self.get_chat(sender, receiver)["income_chat"]

        history_hash = hashlib.sha256(str(income_chat).encode()).hexdigest()
        return history_hash, len(income_chat)

    def get_chat(self, sender, receiver):

        path, file_path = self.get_file_path(sender, receiver)

        try:
            with open(file_path, 'r') as in_box_file:
                chat = json.load(in_box_file)
        except FileNotFoundError :
            chat = {"income_chat":[]}
        except json.JSONDecodeError:
            chat = {"income_chat":[]}

        return chat
    
    def verify_message(self, message : Message):       
        
        try:
            with open(USER_INFO_PATH + message.username + ".json", 'r') as user_file:

                user = json.load(user_file)
                user_public_signature = user["public_signature"]

                base64_decoded_text = base64.b64decode(message.text)

                if(not verify_signature(user_public_signature, message.signature, base64_decoded_text + message.time.encode() + message.receiver_username.encode())):
                    raise Exception("Message refused: can't verify the signature")
                
                base64_decoded_receiver_key = base64.b64decode(message.receiver_key)
                base64_decoded_sender_key = base64.b64decode(message.sender_key)

                if(message.receiver_key != "None" and 
                   message.receiver_key != "" and 
                   message.sender_key != "None" and 
                   message.sender_key != "" and 
                   not verify_signature(user_public_signature, message.key_signature, base64_decoded_receiver_key + base64_decoded_sender_key)):
                    raise Exception("Message refused: can't verify chat key the signature")
                
                # message_datetime = datetime.strptime(message.time,"%Y-%m-%d %H:%M:%S.%f%z")
                # now = datetime.now(timezone.utc)

                # if(now < message_datetime and (now - message_datetime).total_seconds() > 30):
                #     raise Exception("Message refused: inconsistent message date time")
        except FileNotFoundError:
            raise Exception("Message refused: user unknown")