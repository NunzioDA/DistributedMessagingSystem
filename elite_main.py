from model.elite_server import *


el1 = EliteServer(1234)
el2 = EliteServer(1235)

el2.wait_for_threads()