from datetime import datetime, timezone
import json
import os
import socket
import threading

from communication_API.consts import USER_INFO_PATH
from communication_API.server_API import get_version, notify_client_address, send_message
from communication_API.socket_communication import receive_data
from communication_API.client_API import *
from dms_secure.cryptography import encrypt_message, generate_aes_key
from dms_secure.hashing import hash_to_range
from model.dmsnetwork import DMSNetwork
from model.message import Message
from model.msg_manager import MessageManager
from dms_secure.signature_management import *
from dms_secure.rsa import *
from dms_secure.cryptography import *

class Client:
      
    INBOX_PATH = "/inbox/"
    SENT_PATH = "/sent/"
    
    def __init__(self, address, username, password):
        self.address = address
        self.username = username
        self.password = password        

        base_data_path = "./data/client/" + str(self.address)

        self.INBOX_PATH = base_data_path + self.INBOX_PATH
        self.SENT_PATH = base_data_path + self.SENT_PATH

        self.message_manager = MessageManager(
            self.INBOX_PATH, 
            self.address,
            self.username,
            self.SENT_PATH
        )

        self.network_manager = self.network = DMSNetwork(username,address,base_data_path)

        # Definisco la coda di messaggi
        self.messages_queue = []
        self.messages_queue_lock = threading.Lock()
        self.message_notification_listeners = []
        self.chat_update_notification_listeners = []

    def start_client(self, join_threads = True):
        self.running = True

        if(not self._is_user_registered()):
            self.register_user()
        else:
            if(not self.verify_password()):
                raise Exception("Wrong password")
            
        self.init_paths()
            
        self._log("discovering network...")
        try:
            discover_result = self.network.discover()
        except Exception as e:
            self._log("some error occurred -> "+ str(e))
            discover_result = False
        if(discover_result != False):
            self._log("network discovering complete succesfully -> " + str(discover_result) + " servers found")
        else: 
            self._log("couldn't find any server in the network.")

        self._log("Notifing address to servers...")
        self._notify_address()

        self._log("Starting inbox listener...")
        self._inbox_listener_thread = threading.Thread(target=self._inbox_listener)
        self._inbox_listener_thread.start()

        self._log("Starting queue handler...")
        self.queue_handler_thread = threading.Thread(target=self._queue_handler)
        self.queue_handler_thread.start()

        if(join_threads):
            self.queue_handler_thread.join()
            self._inbox_listener_thread.join()

    def init_paths(self):
        if(not os.path.exists(self.INBOX_PATH)):
            os.makedirs(self.INBOX_PATH)

    def close(self):
        self.running = False
        self.server_socket.close()
        send_and_get_response(self.address,["",""])
        

    def add_message_notification_listener(self, listener):
        self.message_notification_listeners.append(listener)

    def notify_message_notification_listeners(self, message : Message):
        for listener in self.message_notification_listeners:
            listener(self.decrypt_message(message))

    def add_chat_update_notification_listener(self, listener):
        self.chat_update_notification_listeners.append(listener)

    def notify_chat_update_notification_listeners(self):
        for listener in self.chat_update_notification_listeners:
            listener()

    def decrypt_message(self, message : Message):
        if(message.receiver_username == self.username):
            _key = base64.b64decode(message.receiver_key)
        else:
            _key = base64.b64decode(message.sender_key)

        private_rsa, salt = self.fetch_user_private_rsa_key(self.username)
        decripted_key = decrypt_message_RSA(_key, self.password.encode(), private_rsa, salt)

        text = base64.b64decode(message.text)
        text = decrypt_message(text,decripted_key).decode()

        return Message(
            message.username,
            message.receiver_username,
            "",
            text,
            message.time,
        )

    def get_full_chat(self, other_user):
        chat_sent = self.message_manager.get_chat(self.username, other_user)["income_chat"]
        chat_received = self.message_manager.get_chat(other_user, self.username)["income_chat"]


        chat_sent = [self.decrypt_message(self.message_manager._create_message_from_chat(self.username, other_user, message)) for message in chat_sent]
        chat_received = [self.decrypt_message(self.message_manager._create_message_from_chat(other_user, self.username, message)) for message in chat_received]

        full_chat = chat_sent + chat_received
        full_chat.sort(key=lambda message: datetime.strptime(message.time,"%Y-%m-%d %H:%M:%S.%f%z"))
        
        return full_chat
    
    def _is_user_registered(self):
        return os.path.exists(USER_INFO_PATH + self.username + ".json")

    def register_user(self):

        rsa_private, salt = generate_RSA_private_key(self.password.encode()) 

        with open(USER_INFO_PATH + self.username + ".json", "w") as user_info_file:
            rsa_private_b64 = base64.b64encode(rsa_private).decode()

            rsa_public = generate_RSA_public_key(self.password.encode(), rsa_private, salt)
            rsa_public_b64 = base64.b64encode(rsa_public).decode()

            salt_b64 = base64.b64encode(salt).decode()

            json.dump({
                "public_signature": generate_signature_public_key(self.password.encode()),
                "private_rsa": rsa_private_b64,
                "public_rsa": rsa_public_b64,
                "salt_rsa": salt_b64
            }, user_info_file)

    def verify_password(self):
         with open(USER_INFO_PATH + self.username + ".json", "r") as user_info_file:
            user_info = json.load(user_info_file)
            return generate_signature_public_key(self.password.encode()) == user_info["public_signature"]
                

    def _inbox_listener(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        server_address = ('localhost', self.address)
        self.server_socket.bind(server_address)
        self.server_socket.listen(1)

        try:
            #Ciclo di gestione client parallela       
            self._log("Server listening for socket connections...")           
            client_socket, client_address = self.server_socket.accept()

            # Avvio thread di gestione delle richieste
            handler_thread = threading.Thread(target=self._request_handler, args=(client_socket,))
            handler_thread.start()

            if(self.running):
                threading.Thread(target=self._inbox_listener).start()
        except KeyboardInterrupt:
            self._log("Interruzione da tastiera. Chiudo il socket...")
            self.on_close()          

        except Exception as e:
            self._log("Error:", e)
        
        self._log("socket listener terminated")     

    def _queue_handler(self):
        if(len(self.messages_queue)>0):
            # Acquisisco il blocco sulla coda
            self.messages_queue_lock.acquire()

            # Eseguo le operazioni sulla coda
            first_message = self.messages_queue.pop(0)

            # Rilascio il blocco sulla coda
            self.messages_queue_lock.release()

            # Salvo il messaggio
            saved = self.message_manager.save_message(first_message)

            if(saved and first_message.username != self.username and first_message.notifiable):
                self.notify_message_notification_listeners(first_message)

            if(first_message.notify_update_listener):
                self.notify_chat_update_notification_listeners()
        
        if(self.running):
            threading.Thread(target=self._queue_handler).start()
        else:    
            self._log("Queue handler terminated")

    def _request_handler(self, client_socket):
        try:
            request = receive_data(client_socket).decode()

            parameters = request.split(";")

            sender_address = parameters.pop(0)
            command = parameters.pop(0)

            if(command == RECEIVE_MSG):
                msg_json = parameters.pop(0)
                message = Message.from_json(msg_json)
                self._handle_receive_message_request(client_socket, message)

            client_socket.close()
        except Exception as e:
            print (e)

    def _handle_receive_message_request(self, client_socket, message : Message):
        try:
            self.message_manager.verify_message(message)

            if(message.receiver_username != self.username):
                raise Exception("Incorrect receiver username: " + message.receiver_username)
            
            self.messages_queue_lock.acquire()

            # Eseguo le operazioni sulla coda
            self.messages_queue.append(message)

            # Rilascio il blocco sulla coda
            self.messages_queue_lock.release()

            send_all(client_socket, b"OK")
        except Exception as e:
            send_all(client_socket,str(e).encode())


    def _notify_address(self):
        for server in self._my_inbox_servers():
            notify_client_address(server, self.username, self.password, self.address)

    def update_chat(self, receiver_username):
        receiver_servers = self._user_inbox_servers(receiver_username)
        my_servers = self._user_inbox_servers(self.username)            

        # Aggiorna messaggi inviati dall'utente
        result_sent = self.message_manager._update_chat(
            self.username, 
            receiver_username, 
            receiver_servers, 
            self.messages_queue_lock, 
            self.messages_queue
        )

        # Aggiorna messaggi ricevuti dall'utente
        result_received = self.message_manager._update_chat(
            receiver_username, 
            self.username, 
            my_servers, 
            self.messages_queue_lock, 
            self.messages_queue,
        )

        if(not result_sent and not result_received):
            self.notify_chat_update_notification_listeners()
            
    def send_message(self, receiver_username, text):      

        chat_key = generate_aes_key()
        my_public_rsa = self.fetch_user_public_rsa_key(self.username)
        receiver_public_rsa = self.fetch_user_public_rsa_key(receiver_username)

        sender_encripted_chat_key = encrypt_message_RSA(chat_key, my_public_rsa)
        receiver_encripted_chat_key = encrypt_message_RSA(chat_key, receiver_public_rsa)

        base64_sender_encripted_chat_key = base64.b64encode(sender_encripted_chat_key).decode('utf-8')
        base64_receiver_encripted_chat_key = base64.b64encode(receiver_encripted_chat_key).decode('utf-8')

        text = encrypt_message(text.encode(), chat_key)

        base64_text = base64.b64encode(text).decode('utf-8')
        date_time = str(datetime.now(timezone.utc))
        signature = sign_message(self.password, text + date_time.encode() + receiver_username.encode())

        keys_signature = sign_message(self.password, receiver_encripted_chat_key+sender_encripted_chat_key)

        message = Message(
            self.username, 
            receiver_username, 
            signature, 
            base64_text, 
            date_time, 
            base64_receiver_encripted_chat_key, 
            base64_sender_encripted_chat_key,
            keys_signature
        )

        for server in self._user_inbox_servers(receiver_username):
            # Chiamata API
            response = send_message(server, message)

            if(response != False and b"OK" in response):
                return True
        
        return False

    
    def fetch_user_public_rsa_key(self, username):
        with open(USER_INFO_PATH + username + ".json", "r") as user_info_file:
            user_info = json.load(user_info_file)
            return base64.b64decode(user_info["public_rsa"])
    
    def fetch_user_private_rsa_key(self, username):
        with open(USER_INFO_PATH + username + ".json", "r") as user_info_file:
            user_info = json.load(user_info_file)
            return base64.b64decode(user_info["private_rsa"]), base64.b64decode(user_info["salt_rsa"])

    def connection_to_mybox():
        raise NotImplementedError("Not implemented")
    
    def _my_inbox_servers(self):
        return self._user_inbox_servers(self.username)
        
    def _user_inbox_servers(self, username):
        servers = self.network_manager.get_network()  
        user_inbox_id = hash_to_range(username.encode(), len(servers))
        return servers[user_inbox_id]
    
    def _log(self, log):
        print("CLIENT [" + str(self.address) + "]: " + str(log))