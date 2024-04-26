import socket

# Message to request network discovery
# other parameters: username and server id
DISCOVERY_MSG = "DISCOVERY" 

# Message to request server ernollment
# other parameters: server id
ENROLL_MSG = "ENROLL" 

def request_network_discovery(elite_server_address, username, server_id):
    server_address = ('localhost', elite_server_address)
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        client_socket.connect(server_address)
        message = DISCOVERY_MSG + ";" + username + ";" + str(server_id)
        client_socket.sendall(message.encode())

        while True:
            data = client_socket.recv(1024)
            if(not data):
                break

        client_socket.close()
    except socket.error as e:
        print("Connection failed:", e)
        return False
    
def enroll_server(elite_server_address, server_id):
    server_address = ('localhost', elite_server_address)
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        client_socket.connect(server_address)
        message = ENROLL_MSG + ";" + str(server_id)
        client_socket.sendall(message.encode())

        data = client_socket.recv(1024)            

        print("Dati ricevuti dal server:", data.decode())

        client_socket.close()
        return data.decode() == "OK"
    except socket.error as e:
        print("Connection failed:", e)
        return False