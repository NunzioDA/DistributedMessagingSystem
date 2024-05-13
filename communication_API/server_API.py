# Comando per inviare messaggi
# richiede anche: id destinatario, firma, messaggio criptato
import base64
from datetime import datetime, timezone

import socket
from communication_API.socket_communication import *
from model.message import Message
from dms_secure.signature_management import sign_message


SEND_MSG = "SEND"
RANGE_MSG = "RANGE"
VERSION_MSG = "VERSION"
SOCIAL_TREE_MSG = "SOCIAL_TREE"
NOTIFY_ADDRESS_MSG = "NOTIFY_ADDRESS"
NEW_SERVER_MSG = "NEW_SERVER_MSG"


def send_message(address, message : Message, sender_address = ""):

    if(message.receiver_key is None or message.sender_key is None):
        message.receiver_key = "None"
        message.sender_key = "None"
        message.key_signature = "None"

    return send_and_get_response(
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

    return send_and_get_response(
        address, 
        [
            str(sender_address),
            RANGE_MSG,
            message_start_j,
            message_end.to_json()           
        ]
    )

def get_version(address, chat_sender, chat_receiver, sender_address = ""):
    return send_and_get_response(
        address, 
        [
            str(sender_address),
            VERSION_MSG,
            chat_sender,
            chat_receiver        
        ]
    )

def get_social_tree(address, sender_address = ""):
    return send_and_get_response(
        address, 
        [
            str(sender_address),
            SOCIAL_TREE_MSG,
        ]
    )

def new_server_in_cluster(address, new_server, sender_address=""):
    return send_and_get_response(
        address, 
        [
            str(sender_address),
            NEW_SERVER_MSG,
            new_server
        ]
    )

def notify_client_address(address, username, private_signature_key, sender_address = 0):
    server_address = ('localhost', address)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        server_socket.connect(server_address)
        message = str(sender_address) + ";" + NOTIFY_ADDRESS_MSG
        send_all(server_socket, message.encode())

        salt = receive_data(server_socket)
        signature = sign_message(private_signature_key, salt + username.encode() + str(sender_address).encode())

        message = username + ";" + signature 

        send_all(server_socket, message.encode())

        response = receive_data(server_socket)

        server_socket.close()
    except socket.error as e:
        print("SERVER API ERROR Connection failed["+str(address)+"]:", e)
        return False
    
    return response