# generate a random topo
import sys
import os
import random
import json
import argparse

class Node():
    def __init__(self, nodeid, rr_client=False):
        self.nodeid = nodeid
        self.neighbors = {}
        self.rr_client = rr_client

    def connect(self, node, weight, is_client=False):
        self.neighbors[node.nodeid] = {'w': weight, 'is_client': is_client}

def topo_to_file(topo):
    buff = ''
    size = len(topo)
    for node in topo.values():
        for n in node.neighbors:
            buff += '%d|%d|%d\n' % (node.nodeid, n, node.neighbors[n]['w'])
    with open('dataset/bgp/topo/rr_%d.txt'%size, 'w') as f:
        f.write(buff)
        f.close()
    bgp_conf = {}
    # write BGP configuration...
    for r in topo.values():
        bgp_conf[r.nodeid] = {}
        for n in r.neighbors: bgp_conf[r.nodeid][n] = {'route-reflector-client': r.neighbors[n]['is_client']}

    bgp_announcements = {}
    # pick some RC and write some announcements.. 
    bgp_nodes = random.sample([n.nodeid for n in topo.values() if n.rr_client], int(len(topo) * 0.2))
    if bgp_nodes == []: bgp_nodes = [random.choice([n.nodeid for n in topo.values() if n.rr_client])]
    for b in bgp_nodes:
        deriv = random.randint(1, 10)
        bgp_conf[b]['external'] = {}
        if deriv > 5: bgp_conf[b]['external']['pref'] = 4
        else: bgp_conf[b]['external']['pref'] = 3
        bgp_announcements[b] = {
            "length": random.randint(1, 5), 
            "med": random.randint(1, 10)
        }

    fconf = open('dataset/bgp/conf/conf_%d.json' % size, 'w')
    fannouncements = open('dataset/bgp/announcements/announcements_%d.json' % size, 'w')
    json.dump(bgp_conf, fconf)
    json.dump(bgp_announcements, fannouncements)
    fconf.close()
    fannouncements.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='generating a topology with route reflection')
    parser.add_argument('-r', '--route-reflector', type=int, help='number of route reflector groups')
    parser.add_argument('-p', type=int, help='number of RRs in a RR group')
    parser.add_argument('-c', '--client', type=int, help='number of route reflector clients per RR')
    node_list = {}
    args = parser.parse_args()
    print(args)
    # generate route reflectors
    next_router_id = 1
    all_rrs = []
    for g in range(args.route_reflector):
        route_reflectors = []
        for r in range(args.p):
            node_list[next_router_id] = Node(next_router_id)
            route_reflectors.append(next_router_id)
            all_rrs.append(next_router_id)
            next_router_id += 1
        # generate clients... 
        for c in range(args.client):
            node_list[next_router_id] = Node(next_router_id, True)
            for r in route_reflectors: 
                w = random.randint(2, 10)
                node_list[r].connect(node_list[next_router_id], w, True)
                node_list[next_router_id].connect(node_list[r], w, False)
            next_router_id += 1

    for r1 in all_rrs:
        for r2 in all_rrs: 
            if r1 > r2: 
                w = random.randint(2, 10)
                node_list[r1].connect(node_list[r2], w, False)
                node_list[r2].connect(node_list[r1], w, False)

    topo_to_file(node_list)
    