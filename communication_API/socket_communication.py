import socket

END_MESSAGE_BYTE = b'\x00'


def send_and_get_response(address, command):
    server_address = ('localhost', address)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        server_socket.connect(server_address)
        message = ";".join(command)
        send_all(server_socket,message.encode())

        response = receive_data(server_socket)
        

        server_socket.close()
    except socket.error as e:
        print("Connection failed["+ str(address) +"]:", e)
        return False
    
    return response

def receive_data(_socket):
    response = b""
    
    while True:
        data = _socket.recv(1024)
        if(not data):
            break
        response += data

        if b'\x00' in data:
            response = response[:-1]
            break
        
    return response

def send_all(_socket, message):
    _socket.sendall(message+END_MESSAGE_BYTE)