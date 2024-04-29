import socket


def send(address, command):
    server_address = ('localhost', address)
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        client_socket.connect(server_address)
        message = ";".join(command)
        client_socket.sendall(message.encode())

        response = b""

        while True:
            data = client_socket.recv(1024)
            if(not data):
                break

            response += data
        

        client_socket.close()
    except socket.error as e:
        print("Connection failed:", e)
        return False
    
    return response