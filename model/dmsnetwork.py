import json
import os
import threading
import communication_API.elite_servers_API as elite_server
from dms_secure.hashing import hash_to_range


class DMSNetwork:    

    def __init__(self, username, address, base_data_path, is_server=False):
        self.username = username
        self.address = address
        self.is_server = is_server
        self.NETWOWK_PATH = base_data_path + "/network/"
        self.NETWOWK_FILE_PATH = self.NETWOWK_PATH + "/servers.json"
        self.discovering_thread_active = False
        self.network_file_lock = threading.Lock()
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

                    self.save_network(result)
                    break
            
            if(result!=False):
                l = 0
                # Conteggio server trovati
                for c in result:
                    l += len(c)
                result = l

            return result
    
    def save_network(self, content):
        self.network_file_lock.acquire()
        with open(self.NETWOWK_FILE_PATH, "w") as servers_file:
            json.dump(content, servers_file)
        self.network_file_lock.release()

    def get_network(self):
        self.network_file_lock.acquire()
        with open(self.NETWOWK_FILE_PATH, "r") as servers_file:
            network = json.load(servers_file)
        self.network_file_lock.release()

        return network    

    def clusters_number(self):
        return len(self.get_network())

    def my_cluster_id(self):
        if(self.is_server):
            tag = str(self.address)
        else:
            tag = self.username

        return hash_to_range(tag.encode(), self.clusters_number())

    def my_cluster(self):

        if(self.is_server):
            tag = str(self.address)
        else:
            tag = self.username

        clusters = self.get_network()        
        my_cluster_id = hash_to_range(tag.encode(), len(clusters))
                
        my_cluster = clusters[my_cluster_id]
        if(self.is_server):
            my_cluster.remove(self.address)
        return my_cluster

    def add_server_to_network(self, server_address):
        new_server_cluster = hash_to_range(str(server_address).encode(), self.clusters_number())
        clusters = self.get_network()
        if(server_address not in clusters[new_server_cluster]):
            clusters[new_server_cluster].append(server_address)
            self.save_network(clusters)

    def _dicover_thread(self):
        while self.discovering_thread_active:
            self.discover()

    def start_discoverer_thread(self):
        if(not self.discovering_thread_active):
            self.discovering_thread_active = True
            threading.Thread(target=self._dicover_thread).start()
    
    def stop_discoverer_thread(self):
        self.discovering_thread_active = False