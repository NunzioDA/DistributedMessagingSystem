import json
import os
import threading
import communication_API.elite_servers_API as elite_server


class DMSNetwork:    

    def __init__(self, username, address, base_data_path, is_server=False):
        self.username = username
        self.address = address
        self.is_server = is_server
        self.NETWOWK_PATH = base_data_path + "/network/"
        self.NETWOWK_FILE_PATH = self.NETWOWK_PATH + "/servers.json"
        self.discovering_thread_active = False
        self.init_path()

    def init_path(self):
        if(not os.path.exists(self.NETWOWK_PATH)):
            os.makedirs(self.NETWOWK_PATH)

        if(not os.path.exists(self.NETWOWK_FILE_PATH)):
            with open(self.NETWOWK_FILE_PATH, 'w') as server_file:
                json.dump([[],[],[]], server_file)

    def discover(self):        

        with open('./res/known_servers.json', 'r') as known_servers_file:
            known_elite_servers = json.load(known_servers_file)

            server_id = None

            if(self.is_server):
                server_id = self.address

            for address in known_elite_servers:
                result =  elite_server.request_network_discovery(address, self.username, server_id)
                
                if(result != False):
                    result = json.loads(result)

                    there_are_empty_clusters = False

                    for cluster in result:
                        if(len(cluster) == 0):
                            there_are_empty_clusters = True
                            self.start_discoverer_thread()
                            break

                    if(not there_are_empty_clusters):
                        self.stop_discoverer_thread()

                    with open(self.NETWOWK_FILE_PATH, "w") as servers_file:
                        json.dump(result, servers_file)
                    break
            
            if(result!=False):
                l = 0
                # Conteggio server trovati
                for c in result:
                    l += len(c)
                result = l

            return result
    
    def _dicover_thread(self):
        while self.discovering_thread_active:
            self.discover()

    def start_discoverer_thread(self):
        if(not self.discovering_thread_active):
            self.discovering_thread_active = True
            threading.Thread(target=self._dicover_thread).start()
    
    def stop_discoverer_thread(self):
        self.discovering_thread_active = False