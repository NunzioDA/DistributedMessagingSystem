from model.server import *

server3 = Server(1124,"")
server3.start_server()

server3.wait_for_threads()