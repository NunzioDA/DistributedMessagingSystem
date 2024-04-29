import base64
from datetime import datetime, timezone
import hashlib
import os
import json
import socket
import threading
from model.client import Client
from model.dmsnetwork import DMSNetwork
from model.message import Message
from communication_API.server_API import *
from dms_secure.hashing import hash_to_range
from dms_secure.signature_management import verify_signature
from communication_API.server_API import send_message, get_chat_range, get_version
from communication_API.elite_servers_API import *

class Server(Client):
      
    INBOX_PATH = "/inbox/"
    USERS_PATH = "/users/"
    NETWORK_PATH = "/network/"

    SERVERS_FILE = "servers.json"
    KNOWN_SERVER_FILE = "./res/known_servers.json"

    def __init__(self, address, username):
        self.network = DMSNetwork(username,address)
        self.address = address
        self.username = username
        self.data_file_path = "./data/" + str(self.address)

        # Definisco la coda di messaggi
        self.messages_queue = []
        self.messages_queue_lock = threading.Lock()

        self.init_paths()        
        
    def init_paths(self):
        if(not os.path.exists(self.data_file_path + self.INBOX_PATH)):
            os.makedirs(self.data_file_path + self.INBOX_PATH)

        if(not os.path.exists(self.data_file_path + self.USERS_PATH)):
            os.makedirs(self.data_file_path + self.USERS_PATH)


    def discover_network(self):
        self.network.discover()

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

        self.socket_listener_thread = threading.Thread(target=self.socket_listener, args=(self.address,))
        self.socket_listener_thread.start()

        self.queue_handler_thread = threading.Thread(target=self._queue_handler)
        self.queue_handler_thread.start()

        self.queue_handler_thread.join()
        self.socket_listener_thread.join()
            
    def propagate_message(self, message : Message):
        with open(self.data_file_path + self.NETWORK_PATH + self.SERVERS_FILE, 'r') as servers_file:
            clusters = json.load(servers_file)

            servers_in_cluster = clusters[self._my_cluster_id()]

            history_hash, version = self._get_version(message.receiver_username, message.username)

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
                version
            )


            for address in servers_in_cluster:
                if(address != self.address):                    
                    threading.Thread(target=send_message, args=(address, message_copy, self.address)).start()

    def _start_enrollment_procedure(self):
        with open(self.KNOWN_SERVER_FILE, "r") as known_servers:
            for elite_server in json.load(known_servers):
                if(enroll_server(elite_server, self.address)):
                    break

    def _sort_queue(self):
        pass
        # self.messages_queue.sort(key=lambda x: x.urgent, reverse=True)

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
                self._save_message(first_message)
                
    def _start_new_chat_scanner(self,):
        threading.Thread(target=self._new_chat_scanner).start()

    def _new_chat_scanner(self):
        cluster = self._my_cluster()

        for server in cluster:
            social_tree = get_social_tree(server,self.address)
            social_tree = json.loads(social_tree)
            
            for receiver in social_tree.keys():
                if(not self._user_inbox_exists(receiver)):
                    os.makedirs(self.data_file_path + self.INBOX_PATH+receiver)

                for sender in social_tree[receiver]:
                    if(not self._user_chat_exists(receiver, sender)):
                        chat_update = get_chat_range(server, None, Message(sender, receiver,"","",str(datetime.now(timezone.utc))), self.address)
                        chat_update = json.loads(chat_update)
                        
                        new_messages_list = [self._create_message_from_chat(sender, receiver, x) for x in chat_update]

                        self.messages_queue_lock.acquire()
                        self.messages_queue[0:0] = new_messages_list
                        self.messages_queue_lock.release()
                            

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
            data = client_socket.recv(1024)
            parameters = data.decode().split(";")

            sender_address = parameters.pop(0)
            command = parameters.pop(0)
            
            
            if(command == SEND_MSG):
                message_json = parameters.pop(0)
                new_message = Message.from_json(message_json)
                self._send_message_request_handler(client_socket, sender_address, new_message)

            elif(command == RANGE_MSG):
                message_start_json = parameters.pop(0)
                message_end_json = parameters.pop(0)
                
                self._range_request_handler(client_socket, sender_address, message_start_json, message_end_json)
            elif(command == VERSION_MSG):
                chat_sender = parameters.pop(0)
                chat_receiver = parameters.pop(0)
                chat_hash, version = self._get_version(chat_sender, chat_receiver)
                client_socket.sendall(json.dumps({"hash":chat_hash, "version":version}).encode())
            elif(command == SOCIAL_TREE_MSG):
                social_tree = self._get_social_tree()
                client_socket.sendall(json.dumps(social_tree).encode())

            client_socket.close()
        finally:
            client_socket.close()


    def _send_message_request_handler(self, client_socket, sender_address, new_message : Message):        
        try:
            # Verifica del messaggio
            self._verify_message(new_message)

            if(new_message.history_hash != ""):
                threading.Thread(target= self._check_history_and_update, args=(new_message,sender_address)).start()

            if(not os.path.exists(self.data_file_path +self.INBOX_PATH + new_message.receiver_username)):
                os.mkdir(self.data_file_path +self.INBOX_PATH + new_message.receiver_username)

            if(new_message.urgent == 1):
                self.propagate_message(new_message)

            # Blocco la coda dei messaggi e aggiungo il messaggio appena ricevuto
            self.messages_queue_lock.acquire()

            self.messages_queue.append(new_message)

            self.messages_queue_lock.release()

            client_socket.sendall(b"OK")
        except Exception as e:
            client_socket.sendall(str(e).encode())


    def _range_request_handler(self,client_socket, sender_address, message_start_json, message_end_json):
        if(message_start_json!="None"):
            message_start = Message.from_json(message_start_json)
        else:
            message_start = None

        message_end = Message.from_json(message_end_json)

        range = self._get_range(message_start, message_end)

        client_socket.sendall(json.dumps(range).encode())

         
    def _save_message(self, message : Message):     
        
        chat = self._get_chat(message.username, message.receiver_username)

        with open(self.data_file_path + self.INBOX_PATH +message.receiver_username + "/" + message.username + ".json", 'w') as in_box_file:
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
                    if(old_datetime < message_datetime):
                        chat["income_chat"].insert(i + 1, json_message)
                        break
            else:
                chat["income_chat"].append(json_message)
            json.dump(chat, in_box_file)

    def _get_chat(self, sender, receiver):
        try:
            with open(self.data_file_path + self.INBOX_PATH + receiver + "/" + sender + ".json", 'r') as in_box_file:
                chat = json.load(in_box_file)
        except FileNotFoundError :
            chat = {"income_chat":[]}
        except json.JSONDecodeError:
            chat = {"income_chat":[]}

        return chat


    def _verify_message(self, message : Message):
        with open(self.data_file_path + self.NETWORK_PATH + self.SERVERS_FILE, 'r') as servers_file:
            clusters = json.load(servers_file)

            if(hash_to_range(message.receiver_username.encode(), len(clusters)) != self._my_cluster_id()):
                raise Exception("User does not belong to this cluster")
        
        try:
            with open(USER_INFO_PATH + message.username + ".json", 'r') as user_file:

                user = json.load(user_file)
                user_public_signature = user["public_signature"]

                base64_decoded_text = base64.b64decode(message.text)

                if(not verify_signature(user_public_signature, message.signature, base64_decoded_text + message.time.encode())):
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
        
    def _get_version(self, sender, receiver):
        income_chat = self._get_chat(sender, receiver)["income_chat"]

        history_hash = hashlib.sha256(str(income_chat).encode()).hexdigest()
        return history_hash, len(income_chat)

    def _check_history_and_update(self, message: Message, sender_address):
        if(not self._check_history_hash(self, message, sender_address)):
            self._update_chat(message.username, message.receiver_username)

    def _check_history_hash(self, message : Message, sender_address):
        income_chat = self._get_chat(message.username, message.receiver_username)["income_chat"]

        end_index = len(income_chat)

        if(end_index>0):
            message_time = datetime.strptime(message.time,"%Y-%m-%d %H:%M:%S.%f%z")

            for i in range(len(income_chat) - 1, -1, -1):
                old_message = income_chat[i]
                old_message_time = datetime.strptime(old_message["date_time"],"%Y-%m-%d %H:%M:%S.%f%z")

                if(old_message_time < message_time):
                        end_index = i + 1
                        break

        
        history_hash = hashlib.sha256(str(income_chat[:end_index]).encode()).hexdigest()
        version = len(income_chat[:end_index])

        return message.history_hash != history_hash and message.version > version

    def _update_chat(self, sender,receiver):
        servers = self._my_cluster()

        most_uptodate_server_address = 0
        latest_version = 0

        for server in servers:
            if(server != self.address):
                try:
                    response = get_version(server, sender, receiver, self.address)
                except Exception as e:
                    response = "{\"hash\": 0, version: 0}"
                response = json.loads(response)

                self._log("HASH: "+response["hash"])

                if(response["version"]>latest_version):
                    most_uptodate_server_address = server
                    latest_version = response["version"]

        self._log(most_uptodate_server_address)

        try:

            if(most_uptodate_server_address != 0):
                hash_chat, version = self._get_version(sender, receiver)

                if(version < latest_version):
                    income_chat = self._get_chat(sender,receiver)["income_chat"]

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

                            income_update = json.loads(get_chat_range(int(most_uptodate_server_address), start_message, end_message))

                            for income_msg in income_update:
                                update_message = self._create_message_from_chat(sender, receiver, income_msg)
                                self._verify_message(update_message)    


                            income_chat[index:index] = income_update

                            self._log(hashlib.sha256(str(income_chat).encode()).hexdigest())

                            self.messages_queue_lock.acquire()
                            self.messages_queue[0:0] = income_update
                            self.messages_queue_lock.release()
                        else:
                            break
        except Exception as e:
            self._log("ERRORE:"+ str(e))

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

        income_chat = self._get_chat(message_end.username, message_end.receiver_username)["income_chat"]

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
        receivers = os.listdir("./data/1222/inbox/")
        social_tree = {}

        for user in receivers:
            sender = os.listdir("./data/1222/inbox/"+user+"/")
            sender =  [x.split('.')[0] for x in sender]
            social_tree[user] = sender
        return social_tree

    def _my_cluster_id(self):
        with open(self.data_file_path + self.NETWORK_PATH + self.SERVERS_FILE, 'r') as servers_info:
            servers = json.load(servers_info)
            
            cluster = -1

            for index, array in enumerate(servers):
                if self.address in array:
                    cluster = index
        return cluster
    
    def _my_cluster(self):
        with open(self.data_file_path + self.NETWORK_PATH + self.SERVERS_FILE, 'r') as servers_info:
            servers = json.load(servers_info)
        
            cluster = None

            for cluster in servers:
                if self.address in cluster:
                    break
                
        return cluster
    
    def _log(self, log):
        print("SERVER [" + str(self.address) + "]: " + str(log))