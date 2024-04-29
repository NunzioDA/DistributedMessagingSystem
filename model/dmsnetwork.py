import json
import communication_API.elite_servers_API as elite_server


class DMSNetwork:    

    def __init__(self, username, address, is_server=False):
        self.username = username
        self.address = address
        self.is_server = is_server

        self.NETWOWK_FILE_PATH = "./data/" + str(self.address) + "/network/servers.json"

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
                    with open(self.NETWOWK_FILE_PATH, "w") as servers_file:
                        json.dump(result, servers_file)
                    break
            
            if(result!=False):
                l = 0
                for c in result:
                    l += len(c)
                result = l
            return result
