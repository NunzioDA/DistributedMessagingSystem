# Comando per inviare messaggi
# richiede anche: id destinatario, firma, messaggio criptato
import base64
from datetime import datetime, timezone

import socket
from communication_API.socket_communication import *
from model.message import Message

USER_INFO_PATH = "./data/users/"


SEND_MSG = "SEND"
RANGE_MSG = "RANGE"
VERSION_MSG = "VERSION"
SOCIAL_TREE_MSG = "SOCIAL_TREE"


def send_message(address, message : Message, sender_address = ""):

    if(message.receiver_key is None or message.sender_key is None):
        message.receiver_key = "None"
        message.sender_key = "None"
        message.key_signature = "None"

    return send(
        address, 
        [
            str(sender_address),
            SEND_MSG,
            message.to_json()
        ]
    )

def get_chat_range(address, message_start : Message, message_end : Message, sender_address = ""):


    if(message_start == None):
        message_start_j = "None"
    else:
        message_start_j = message_start.to_json()

    return send(
        address, 
        [
            str(sender_address),
            RANGE_MSG,
            message_start_j,
            message_end.to_json()           
        ]
    )

def get_version(address, chat_sender, chat_receiver, sender_address = ""):
    return send(
        address, 
        [
            str(sender_address),
            VERSION_MSG,
            chat_sender,
            chat_receiver        
        ]
    )

def get_social_tree(address, sender_address = ""):
    return send(
        address, 
        [
            str(sender_address),
            SOCIAL_TREE_MSG,
        ]
    )