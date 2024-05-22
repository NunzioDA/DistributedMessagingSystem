from datetime import datetime, timezone
import json


class Message:
    def __init__(
            self, 
            username, 
            receiver_username, 
            signature, 
            text, 
            time,
            reciver_key = "",
            sender_key = "",
            key_signature = "", 
            urgent = 1,
            history_hash = "",
            version = 0,
            notifiable=True,
            notify_update_listener=False
        ):
        self.username = username
        self.receiver_username = receiver_username
        self.signature = signature
        self.text = text
        self.receiver_key = reciver_key
        self.sender_key = sender_key
        self.key_signature = key_signature
        self.urgent = urgent
        self.time = time
        self.history_hash = history_hash
        self.version = version
        self.notifiable = notifiable
        self.notify_update_listener = notify_update_listener

    def to_json(self):
        return json.dumps({
            "username" : self.username,
            "receiver_username" : self.receiver_username,
            "signature" : self.signature,
            "text" : self.text,
            "time" : self.time,
            "receiver_key" : self.receiver_key,
            "sender_key" : self.sender_key,
            "key_signature" : self.key_signature,
            "urgent" : self.urgent,
            "history_hash" : self.history_hash,
            "version" : self.version
        })
    
    @classmethod
    def from_json(cls, json_str):
        json_data = json.loads(json_str)
        return cls(
            json_data["username"],
            json_data["receiver_username"],
            json_data["signature"],
            json_data["text"],
            json_data["time"],
            json_data["receiver_key"],
            json_data["sender_key"],
            json_data["key_signature"],
            json_data["urgent"],
            json_data["history_hash"],
            json_data["version"]
        )