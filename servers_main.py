from model.server import *
import os

server = Server(1121,"")
server.start_server()

server1 = Server(1122,"")
server1.start_server()

server2 = Server(1123,"")
server2.start_server()

server3 = Server(1124,"")
server3.start_server()


server2.wait_for_threads()