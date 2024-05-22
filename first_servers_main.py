from model.server import *

server = Server(1121,"")
server.start_server()

server1 = Server(1122,"")
server1.start_server()

server2 = Server(1123,"")
server2.start_server()


server2.wait_for_threads()