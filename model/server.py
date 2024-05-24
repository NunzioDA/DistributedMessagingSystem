import base64
from datetime import datetime, timezone
import hashlib
import os
import json
import secrets
import socket
import threading
from communication_API.client_API import send_message_to_client
from communication_API.consts import USER_INFO_PATH
from model.client import Client
from model.dmsnetwork import DMSNetwork
from model.message import Message
from communication_API.server_API import *
from dms_secure.hashing import hash_to_range
from dms_secure.signature_management import verify_signature
from communication_API.server_API import send_message, get_chat_range, get_version
from communication_API.elite_servers_API import *
from communication_API.socket_communication import *
from model.msg_manager import MessageManager

class Server:
      
    INBOX_PATH = "/inbox/"
    NETWORK_PATH = "/network/"

    KNOWN_SERVER_FILE = "./res/known_servers.json"
    INFO_FILE = "info.json"

    def __init__(self, address, username):
        self.address = address
        self.data_file_path = "./data/servers/" + str(self.address)
        self.init_paths() 

        
        self.network = DMSNetwork(username,address, self.data_file_path, True)
        self.message_manager = MessageManager(
            self.data_file_path + self.INBOX_PATH,
            self.address
        )

        self.username = username
        # Definisco la coda di messaggi
        self.messages_queue = []
        self.messages_queue_lock = threading.Lock()
        
               
        
    def init_paths(self):
        if(not os.path.exists(self.data_file_path + self.INBOX_PATH)):
            os.makedirs(self.data_file_path + self.INBOX_PATH)


    def start_server(self):
            
        self._log("starting enrollment procedure...")
        self._start_enrollment_procedure()
        self._log("enrollment procedure complete")


        self._log("discovering network...")
        try:
            discover_result = self.network.discover()

        except Exception as e:
            self._log("some error occurred -> "+ str(e))
        if(discover_result != False):
            self._log("network discovering complete succesfully -> " + str(discover_result) + " servers found")
        else: 
            self._log("couldn't find any server in the network.")


        self._log("starting new chat scanner...")
        self._start_new_chat_scanner()

        self._log("starting socket listener...")
        self.socket_listener_thread = threading.Thread(target=self.socket_listener, args=(self.address,))
        self.socket_listener_thread.start()

        self._log("starting queue handler...")
        self.queue_handler_thread = threading.Thread(target=self._queue_handler)
        self.queue_handler_thread.start()


    def wait_for_threads(self):
        self.queue_handler_thread.join()
        self.socket_listener_thread.join()

    def save_user_address(self, user, address):
        with open(self.data_file_path + self.INBOX_PATH + user + "/" + self.INFO_FILE, "w") as user_info_file:
            json.dump({"address":address},user_info_file)

    def get_user_address(self, user):
        with open(self.data_file_path + self.INBOX_PATH + user+"/"+self.INFO_FILE, "r") as user_info_file:
            user_info = json.load(user_info_file)
            address = user_info["address"]
        
        return address

    def _forward_message_to_user(self, new_message : Message):
        try:
            address = self.get_user_address(new_message.receiver_username)
            result = send_message_to_client(address,new_message, self.address)
            if(result != False):
                return True
        except Exception as e:
            self._log(e)
        
        return False
     
    def propagate_message(self, message : Message):
        servers_in_cluster = self.network.my_cluster()

        history_hash, version = self.message_manager._get_version(message.username, message.receiver_username)

        message_copy = Message(
            message.username,
            message.receiver_username,
            message.signature,
            message.text,
            message.time,
            message.receiver_key,
            message.sender_key,
            message.key_signature,
            0,
            history_hash,
            version,
            already_forwarded=message.already_forwarded
        )


        latest_version = 0
        latest_version_hash = ""

        for address in servers_in_cluster:
            if(address != self.address):               
                result = send_message(address, message_copy, self.address) 
                if(result != False and b"OK" in result):
                    message_copy.already_forwarded = True
                    splitted_result = result.decode().split(";")
                    server_version = int(splitted_result[1])
                    server_hash = splitted_result[2]
                    if(server_version > latest_version):
                        latest_version = server_version
                        latest_version_hash = server_hash

        my_chat_hash, my_chat_version = self.message_manager._get_version(message.username, message.receiver_username)            

        if(latest_version_hash != "" and (latest_version_hash != my_chat_hash and latest_version == my_chat_version) or latest_version > my_chat_version):
            self._log("Another server has a more recent version of [" + message.username + " -> " + message.receiver_username +"] chat: starting chat update")

            self.message_manager._update_chat(
                message.username, 
                message.receiver_username, 
                self.network.my_cluster(),
                self.messages_queue_lock,
                self.messages_queue,
                verify_message=self._verify_user_belong_to_cluster                
            )

    def _start_enrollment_procedure(self):
        with open(self.KNOWN_SERVER_FILE, "r") as known_servers_f:
            known_servers = json.load(known_servers_f)
            for elite_server in known_servers:
                if(enroll_server(elite_server, self.address)):
                    break

    def _sort_queue(self):
        pass

    def _queue_handler(self):
        while True:
            if(len(self.messages_queue)>0):
                # Acquisisco il blocco sulla coda
                self.messages_queue_lock.acquire()

                # Eseguo le operazioni sulla coda
                self._sort_queue()
                first_message = self.messages_queue.pop(0)

                # Rilascio il blocco sulla coda
                self.messages_queue_lock.release()

                # Salvo il messaggio
                self.message_manager.save_message(first_message)
                
    def _start_new_chat_scanner(self,):
        threading.Thread(target=self._new_chat_scanner).start()

    def _new_chat_scanner(self):
        cluster = self.network.my_cluster()

        for server in cluster:
            social_tree = get_social_tree(server,self.address)
            if(social_tree != False):
                social_tree = json.loads(social_tree)
                
                for receiver in social_tree.keys():
                    if(not self._user_inbox_exists(receiver)):
                        os.makedirs(self.data_file_path + self.INBOX_PATH+receiver)

                    for sender in social_tree[receiver]["senders"]:
                        if(not self._user_chat_exists(receiver, sender)):
                            self._log("New chat found [" + sender + " -> " + receiver + "]")
                            chat_update = get_chat_range(server, None, Message(sender, receiver,"","",str(datetime.now(timezone.utc))), self.address)
                            chat_update = json.loads(chat_update)
                            
                            new_messages_list = [self._create_message_from_chat(sender, receiver, x) for x in chat_update]

                            self.messages_queue_lock.acquire()
                            self.messages_queue[0:0] = new_messages_list
                            self.messages_queue_lock.release()

                    if(not os.path.exists(self.data_file_path + self.INBOX_PATH + receiver + "/" + self.INFO_FILE) and 
                       social_tree[receiver]["address"] != "Unknown"):
                        self.save_user_address(receiver, social_tree[receiver]["address"])

    def _user_inbox_exists(self, user):
        return os.path.exists(self.data_file_path + self.INBOX_PATH+user)

    def _user_chat_exists(self, receiver, sender):
        return os.path.exists(self.data_file_path + self.INBOX_PATH + receiver + "/"+sender+".json")

    # Resta in ascolto delle richieste
    def socket_listener(self, address):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        server_address = ('localhost', address)
        self.server_socket.bind(server_address)
        self.server_socket.listen(1)

        try:
            #Ciclo di gestione client parallela
            while True:           
                self._log("Server listening for socket connections...")           
                client_socket, client_address = self.server_socket.accept()

                # Avvio thread di gestione delle richieste
                handler_thread = threading.Thread(target=self.server_request_handler, args=(client_socket,))
                handler_thread.start()
        except KeyboardInterrupt:
            self._log("Interruzione da tastiera. Chiudo il socket...")
            self.on_close()          

        except Exception as e:
            self._log("Error:", e)        


                
    # Gestisce le richieste
    def server_request_handler(self, client_socket):
        try:
            self._log("Handling connection")
            data = receive_data(client_socket)

            parameters = data.decode().split(";")
            
            sender_address = parameters.pop(0)
            command = parameters.pop(0)
            
            
            if(command == SEND_MSG):
                message_json = parameters.pop(0)
                new_message = Message.from_json(message_json)
                self._log("Send message request [" + str(sender_address) + "]")
                self._send_message_request_handler(client_socket, sender_address, new_message)

            elif(command == RANGE_MSG):
                message_start_json = parameters.pop(0)
                message_end_json = parameters.pop(0)
                self._log("Chat range request [" + str(sender_address) + "]")
                self._range_request_handler(client_socket, sender_address, message_start_json, message_end_json)
            elif(command == VERSION_MSG):
                chat_sender = parameters.pop(0)
                chat_receiver = parameters.pop(0)
                chat_hash, version = self.message_manager._get_version(chat_sender, chat_receiver)
                self._log("Chat version request [" + str(sender_address) + "] : " + chat_sender + " -> " + chat_receiver)
                send_all(client_socket,json.dumps({"hash":chat_hash, "version":version}).encode())
            elif(command == SOCIAL_TREE_MSG):
                social_tree = self._get_social_tree()
                self._log("Social tree request [" + str(sender_address) + "]")
                send_all(client_socket,json.dumps(social_tree).encode())
            elif(command == NOTIFY_ADDRESS_MSG):   
                self._log("Address notification [" + str(sender_address) + "]")  
                self._handle_address_notification(client_socket, sender_address)
            elif(command == NEW_SERVER_MSG):
                new_server = parameters.pop(0)
                self._log("New server in cluster found [" + str(new_server) + "]")  
                self._new_server_in_cluster_handler(client_socket, new_server)

            client_socket.close()
        finally:
            client_socket.close()


    def _new_server_in_cluster_handler(self, client_socket, new_server):
        self.network.add_server_to_network(int(new_server))

    def _send_message_request_handler(self, client_socket, sender_address, new_message : Message):        
        try:
            # Verifica del messaggio
            self._verify_message(new_message)

            if(new_message.history_hash != ""):
                threading.Thread(target= self._check_history_and_update, args=(new_message,sender_address)).start()

            if(not os.path.exists(self.data_file_path +self.INBOX_PATH + new_message.receiver_username)):
                os.mkdir(self.data_file_path +self.INBOX_PATH + new_message.receiver_username)

            if(not new_message.already_forwarded):
                self._log("Forwarding message to user")
                result = self._forward_message_to_user(new_message)
                
                if(result):
                    new_message.already_forwarded = True
                    self._log("Message forwarded succesfully")
                else: self._log("Message forwarding failed")

            if(new_message.urgent == 1):                                
                threading.Thread(target=self.propagate_message, args=(new_message,)).start()               
            

            # Blocco la coda dei messaggi e aggiungo il messaggio appena ricevuto
            self.messages_queue_lock.acquire()

            chat_hash, chat_version = self.message_manager._get_version(new_message.username, new_message.receiver_username)
            self.messages_queue.append(new_message)

            self.messages_queue_lock.release()

            send_all(client_socket, ("OK;" + str(chat_version) + ";" + chat_hash).encode())
        except Exception as e:
            send_all(client_socket,str(e).encode())


    def _range_request_handler(self,client_socket, sender_address, message_start_json, message_end_json):
        if(message_start_json!="None"):
            message_start = Message.from_json(message_start_json)
        else:
            message_start = None

        message_end = Message.from_json(message_end_json)

        range = self._get_range(message_start, message_end)

        send_all(client_socket,json.dumps(range).encode())

    def _verify_message(self, message:Message):
        self._verify_user_belong_to_cluster(message)
        self.message_manager.verify_message(message)

    def _verify_user_belong_to_cluster(self, message:Message):
        if(hash_to_range(message.receiver_username.encode(), self.network.clusters_number()) != self.network.my_cluster_id()):
            raise Exception("User does not belong to this cluster")   

    def _handle_address_notification(self, client_socket, sender_address):
        try:
            salt = secrets.token_bytes(32)
            send_all(client_socket, salt)

            response = receive_data(client_socket).decode()

            split_response = response.split(";")
            username = split_response.pop(0)
            signature = split_response.pop(0)

            with open(USER_INFO_PATH + username + ".json", 'r') as user_file:

                user = json.load(user_file)
                user_public_signature = user["public_signature"]

                if(not verify_signature(user_public_signature, signature, salt + username.encode() + str(sender_address).encode())):
                    raise Exception("Message refused: can't verify the signature")
                
                if(not os.path.exists(self.data_file_path + self.INBOX_PATH + username + "/")):
                    os.mkdir(self.data_file_path + self.INBOX_PATH + username + "/")

                self.save_user_address(username, int(sender_address))

            send_all(client_socket,b"OK")
        except Exception as e:
            send_all(client_socket,str(e).encode())

    def _check_history_and_update(self, message: Message, sender_address):
        if(not self._consistent_history_hash(message, sender_address)):
            self._log("Received a more recent [" + message.username + " -> " + message.receiver_username +"] chat: starting chat update")
            self.message_manager._update_chat(
                message.username, 
                message.receiver_username, 
                self.network.my_cluster(),
                self.messages_queue_lock,
                self.messages_queue,
                verify_message=self._verify_user_belong_to_cluster                
            )

    def _consistent_history_hash(self, message : Message, sender_address):
        try:
            income_chat = self.message_manager.get_chat(message.username, message.receiver_username)["income_chat"]
        except Exception:
            income_chat = []

        
        history_hash = hashlib.sha256(str(income_chat).encode()).hexdigest()
        version = len(income_chat)

        return not((message.history_hash != history_hash and message.version == version) or message.version > version)


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

    def _get_range(self, message_start : Message, message_end : Message):

        message_end_time = datetime.strptime(message_end.time,"%Y-%m-%d %H:%M:%S.%f%z")

        if(message_start != None):
            message_start_time = datetime.strptime(message_start.time,"%Y-%m-%d %H:%M:%S.%f%z")
            if(message_start.receiver_username != message_end.receiver_username or
            message_start.username != message_end.username or 
            message_start_time >= message_end_time):
                return []

        
        try:
            income_chat = self.message_manager.get_chat(message_end.username, message_end.receiver_username)["income_chat"]
        except Exception:
            income_chat = []

        range_chat = []        

        end_index = 0

        for i in range(len(income_chat) - 1, -1, -1):
            message = income_chat[i]
            message_time = datetime.strptime(message["date_time"],"%Y-%m-%d %H:%M:%S.%f%z")

            if(message_start != None and message_time <= message_start_time):
                break

            if(message_time < message_end_time):
                if(message_start != None):
                    range_chat.insert(0, message)
                else:
                    end_index = i + 1
                    break

        if(message_start == None):
            range_chat = income_chat[:end_index]

        return range_chat

    def _get_social_tree(self):
        receivers = os.listdir(self.data_file_path + self.INBOX_PATH )
        social_tree = {}

        for user in receivers:
            senders = os.listdir(self.data_file_path + self.INBOX_PATH + user+"/")
            senders =  [x.split('.')[0] for x in senders] # Rimozione .json 
                            
            if("info" in senders):
                senders.remove("info")

            try:
                address = self.get_user_address(user)
            except Exception as e:
                address = "Unknown"

            social_tree[user] = {"senders":senders, "address":address}
        return social_tree   

    
    def _log(self, log):
        print("SERVER [" + str(self.address) + "]: " + str(log))