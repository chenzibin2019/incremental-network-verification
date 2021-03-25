# generate a random topo
import sys
import os
import random
import json

class Node():
    def __init__(self, nodeid):
        self.nodeid = nodeid
        self.neighbors = {}

    def connect(self, node, weight):
        self.neighbors[node.nodeid] = weight

def topo_to_file(topo):
    buff = ''
    size = len(topo)
    for node in topo.values():
        for n in node.neighbors:
            buff += '%d|%d|%d\n' % (node.nodeid, n, node.neighbors[n])
    with open('fm/topo/fm_%d.txt'%size, 'w') as f:
        f.write(buff)
        f.close()
    # write some announcements.. 
    bgp_nodes = random.sample(list(topo.keys()), int(len(topo) * 0.2))
    if bgp_nodes == []: bgp_nodes = [random.randint(1, len(topo))]
    bgp_pref, bgp_announcements = {}, {}
    for b in bgp_nodes:
        deriv = random.randint(1, 10)
        if deriv > 5: bgp_pref[b] = 4
        else: bgp_pref[b] = 3
        bgp_announcements[b] = {
            "length": random.randint(1, 5), 
            "med": random.randint(1, 10)
        }

    fpref = open('fm/bgp/pref_%d.json'%size, 'w')
    fannouncements = open('fm/bgp/announcement_%d.json'%size, 'w')
    json.dump(bgp_pref, fpref)
    json.dump(bgp_announcements, fannouncements)
    fpref.close()
    fannouncements.close()

if __name__ == '__main__':
    topo_size = int(sys.argv[1])
    node_list = {}

    for i in range(1, topo_size + 1):
        node_list[i] = Node(i)
    
    for i in range(1, topo_size + 1):
        for j in range(i + 1, topo_size + 1):
            node_list[i].connect(node_list[j], random.randint(1, 10))

    topo_to_file(node_list)
    #os.makedirs('conf/%s/configs'%sys.argv[1].split('.')[0])
    #topoToConf(node_list, 'conf', sys.argv[1].split('.')[0])
    # topoToConf(topo, 'tmp/', 'bin', 2)
    # topoToFile(topo, 'files/topo_test_%d.txt'%totalNode, 'files/connections_test_%d.txt'%totalNode)
    # vis(topo)