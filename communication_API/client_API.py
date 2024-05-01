from communication_API.socket_communication import *
from model.message import Message

RECEIVE_MSG = "RECEIVE"

def send_message_to_client(address, message : Message, sender_address =""):
    return send_and_get_response(
        address,
        [
            str(sender_address),
            RECEIVE_MSG,
            message.to_json()
        ]
    )
