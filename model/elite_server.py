
##
## Creato da Nunzio D'Amore
##

import json
import os
import threading
import socket
from communication_API.elite_servers_API import *
from communication_API.server_API import new_server_in_cluster
from dms_secure.hashing import *
import random



## La costante CLIENT_OTHER_CLUSTERS_PERCENTAGE indica
## la percentuale di indirizzi ip da mandare al client
## riguardanti server di cluster a cui il client non appartiene
CLIENT_OTHER_CLUSTERS_PERCENTAGE = 0.1
KNOWN_SERVER_FILE = "./res/known_servers.json"

## Gli elite server conoscono l'initera rete di server 
## e permettono a chiunque di conoscere la rete in base al
## proprio identificatore
##
## Se la richiesta arriva da un server restituisce la risposta
## sia per la rete gestita dal server in base all'ip 
## sia per il funzionamento del client in base all'username
class EliteServer:

    def __init__(self, elite_address):
        self.elite_address = elite_address    

        base_path = "./data/elite/" + str(self.elite_address)

        self.servers_file_path = base_path + "/servers.json"

        if(not os.path.exists(base_path)):
            os.makedirs(base_path)
        
        if(not os.path.exists(self.servers_file_path)):
            with open(self.servers_file_path, "w") as servers_f:
                json.dump([[], [], []], servers_f)


        self.elite_request_handler_thread = threading.Thread(target=self.start_socket_listener, args=[elite_address])
        self.elite_request_handler_thread.start()
        

    def wait_for_threads(self):
        self.elite_request_handler_thread.join()
    

    # Gestisce le richieste di discovery 
    def elite_request_handler(self, client_socket):
        try:
            self._log("Handling connection")
            data = receive_data(client_socket)
            parameters = data.decode().split(";")

            command = parameters[0]
            
            
            if(command == DISCOVERY_MSG):
                username = parameters[1]
                server_id = parameters[2]
                self._log("Network discovery request [" + server_id + "]")
                self.discover_request(client_socket, username, server_id)
            elif(command == ENROLL_MSG):
                server_id = parameters[1]
                propagate = parameters[2]
                self._log("Enroll request [" + server_id + "]")
                self.enroll_server(client_socket, server_id, propagate)
                
            client_socket.close()
        finally:
            client_socket.close()

    # Resta in ascolto delle richieste di discovery
    def start_socket_listener(self, address):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        server_address = ('localhost', address)
        self.server_socket.bind(server_address)
        self.server_socket.listen(1)

        try:
            #Ciclo di gestione client parallela
            while True:           
                self._log("Discovery handler listening...")           
                client_socket, client_address = self.server_socket.accept()

                # Avvio thread di gestione delle richieste
                handler_thread = threading.Thread(target=self.elite_request_handler, args=(client_socket,))
                handler_thread.start()
        except KeyboardInterrupt:
            self._log("Interruzione da tastiera. Chiudo il socket...")
            self.on_close()          

        except Exception as e:
            self._log("Error:", e)
        
            

    def discover_request(self, client_socket, username, server_id):
        with open(self.servers_file_path, 'r') as servers_file:
            clusters = json.load(servers_file)
            user_hash = hash_to_range(username.encode(), len(clusters))

            if(server_id !="None"):
                server_hash = hash_to_range(server_id.encode(), len(clusters))
                
                hashes = [user_hash, server_hash]
            else:
                hashes = [user_hash]

            # Per ogni cluster restituisco all'utente un numero di server pari
            # alla percentuale in CLIENT_OTHER_CLUSTERS_PERCENTAGE sul numero di server
            # nel cluster più uno, selezionando i server in maniera casuale
            #
            # Per il cluster a cui l'utente o il server appartiene, restituisco tutti i nodi
            for i in range(len(clusters)):
                if(i not in hashes):
                    servers_number = int((len(clusters[i]) * 0.1)) + 1
                    if(len(clusters[i]) != 0):
                        clusters[i] = random.sample(clusters[i], servers_number)                    
                else:
                    clusters[i] = clusters[i]
            
        send_all(client_socket,json.dumps(clusters).encode())

    def enroll_server(self, client_socket, server_address, propagate):
        try:
            with open(self.servers_file_path, 'r') as servers_file:
                clusters = json.load(servers_file)

                min_index = hash_to_range(str(server_address).encode(), len(clusters))

                server_already_enrolled = int(server_address) in clusters[min_index]

                if(not server_already_enrolled):
                    clusters[min_index].append(int(server_address))

            with open(self.servers_file_path, 'w') as file:
                json.dump(clusters, file)

            send_all(client_socket,b"OK")

            if(propagate == "1"):
                self.propagate_enroll_request(server_address, clusters[min_index])

        except Exception as e:
            send_all(client_socket,str(e).encode())

        client_socket.close()
        
    def propagate_enroll_request(self,server_address, servers_in_cluster):
        with open(KNOWN_SERVER_FILE, "r") as known_servers:
            for elite_server_address in json.load(known_servers):
                if(elite_server_address != self.elite_address):
                    enroll_server(elite_server_address, server_address, 0)
            
        for server in servers_in_cluster:
            if(int(server) != int(server_address)):
                new_server_in_cluster(server, server_address,self.elite_address)

    def on_close(self):
        self.server_socket.close()
    

    def _log(self, *log):
        print("ELITE[", self.elite_address , "]: ", *log)
