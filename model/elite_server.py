
##
## Creato da Nunzio D'Amore
##

import json
import threading
import socket
from communication_API.elite_servers_API import *
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
        self.servers_file_path = "./data/" + str(self.elite_address) + "/servers.json"

        self.elite_request_handler_thread = threading.Thread(target=self.start_socket_listener, args=[elite_address])
        self.elite_request_handler_thread.start()
        self.elite_request_handler_thread.join()

    # Gestisce le richieste di discovery 
    def elite_request_handler(self, client_socket):
        try:
            print("Handling connection")
            data = client_socket.recv(1024)
            parameters = data.decode().split(";")

            command = parameters[0]
            
            
            if(command == DISCOVERY_MSG):
                username = parameters[1]
                server_id = parameters[2]
                self.discover_request(client_socket, username, server_id)
            elif(command == ENROLL_MSG):
                server_id = parameters[1]
                self.enroll_server(client_socket, server_id)
                
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
                print("Discovery handler listening...")           
                client_socket, client_address = self.server_socket.accept()

                # Avvio thread di gestione delle richieste
                handler_thread = threading.Thread(target=self.elite_request_handler, args=(client_socket,))
                handler_thread.start()
        except KeyboardInterrupt:
            print("Interruzione da tastiera. Chiudo il socket...")
            self.on_close()          

        except Exception as e:
            print("Error:", e)
        
            

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
            
        client_socket.sendall(json.dumps(clusters).encode())

    def enroll_server(self, client_socket, server_address):
        try:
            with open(self.servers_file_path, 'r') as servers_file:
                clusters = json.load(servers_file)

                # La funzione seguente ottiene l'indice dell'array in clusters 
                # con meno elementi, ottenendo il cluster con meno server al suo interno
                min_index = min(range(len(clusters)), key=lambda i: len(clusters[i]))
                
                server_already_enrolled = False

                for cluster in clusters:
                    if(int(server_address) in cluster):
                        server_already_enrolled = True
                        break

                if(not server_already_enrolled):
                    clusters[min_index].append(int(server_address))

                self.propagate_enroll_request(server_address)

            with open(self.servers_file_path, 'w') as file:
                json.dump(clusters, file)

            client_socket.sendall("OK".encode())
        except Exception as e:
            client_socket.sendall(str(e).encode())

        client_socket.close()
        
    def propagate_enroll_request(self,server_address):
        with open(KNOWN_SERVER_FILE, "r") as known_servers:
                    for elite_server_address in json.load(known_servers):
                        if(elite_server_address != self.elite_address):
                            enroll_server(elite_server_address, server_address)
    def on_close(self):
        self.server_socket.close()
    

