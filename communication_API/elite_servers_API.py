import socket
from communication_API.socket_communication import *

# Message to request network discovery
# other parameters: username and server id
DISCOVERY_MSG = "DISCOVERY" 

# Message to request server ernollment
# other parameters: server id
ENROLL_MSG = "ENROLL" 

def request_network_discovery(elite_server_address, username, server_id):
    server_address = ('localhost', elite_server_address)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        server_socket.connect(server_address)
        message = DISCOVERY_MSG + ";" + username + ";" + str(server_id)
        send_all(server_socket, message.encode())

        result = receive_data(server_socket)
            
        server_socket.close()
        return result

    except socket.error as e:
        print("ELITE SERVER API ERROR [elite server " + str(elite_server_address) + "]:", e)
        return False
    
def enroll_server(elite_server_address, server_id, propagate = 1):
    server_address = ('localhost', elite_server_address)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        server_socket.connect(server_address)
        message = ENROLL_MSG + ";" + str(server_id) + ";" + str(propagate)
        send_all(server_socket,message.encode())

        data = receive_data(server_socket)      

        server_socket.close()
        return data.decode() == "OK"
    except socket.error as e:
        print("ELITE SERVER API ERROR Connection failed[elite server " + str(elite_server_address) + "]:", e)
        return False