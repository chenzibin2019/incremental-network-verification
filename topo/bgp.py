import json
from topo.topo import Topo
from topo.node import Node

class BGP(Topo):
    def __init__(self):
        super(BGP, self).__init__()
        self.announcements = {}
        self.max_length = -1
        self.max_cost = -1
        self.connections = []

    def build_from_abstraction(self, args):
        self.load_from_file(args.topo)
        self.load_announcements(args.announcement)
        self.load_preference(args.preference)
        self.build_asm()

    def load_from_file(self, filename):
        with open(filename, 'r') as f:
            for line in f: 
                if line.startswith('#'): continue
                tokens = line.strip('\n').split('|')
                assert len(tokens) >= 3
                node1, node2, w = int(tokens[0]), int(tokens[1]), int(tokens[2])
                node1_ins = self.add_node(node1)
                node2_ins = self.add_node(node2)
                node1_ins.connect(node2_ins, {'w': w})
                node2_ins.connect(node1_ins, {'w': w})
                if w > self.max_cost: self.max_cost = w
                self.connections.append((node1, node2))

    def load_announcements(self, filename):
        with open(filename, 'r') as f:
            announcement = json.load(f)
            tmp_announcement = {}
            field_max = {'med': 100}
            max_length = 0
            for node in announcement: 
                nodeid = int(node)
                tmp_announcement[nodeid] = {'length': 10, 'med': 100}
                for field in announcement[node]:
                    if field in announcement[node]: 
                        tmp_announcement[nodeid][field] = announcement[node][field]
                        if field in field_max and tmp_announcement[nodeid][field] > field_max[field]: 
                            field_max[field] = tmp_announcement[nodeid][field]
                        elif field == 'length' and tmp_announcement[nodeid][field] > max_length:
                            max_length = tmp_announcement[nodeid][field]
            # cleanup 
            for nodeid in self.node_list: 
                if nodeid not in tmp_announcement: 
                    self.node_list[nodeid].params['has_announcement'] = False
                    continue
                self.node_list[nodeid].params['has_announcement'] = True
                self.node_list[nodeid].params['egp_cost'] = (
                    (max_length - tmp_announcement[nodeid]['length']) * field_max['med'] + 
                    (field_max['med'] - tmp_announcement[nodeid]['med'])
                )
            # record max_length
            self.max_length = max_length

    def load_preference(self, filename):
        with open(filename, 'r') as f:
            preference = json.load(f)
            for p in preference:
                if int(p) in self.node_list: 
                    self.node_list[int(p)].params['pref'] = preference[p]
                    self.node_list[int(p)].params['has_configuration'] = True
                else:
                    self.node_list[int(p)].params['has_configuration'] = False

    def build_asm(self):
        for node in self.node_list.values():
            node.buildASMNode('best%d' % node.nodeid, 'best')
            if node.params['has_announcement'] and node.params['has_configuration']: 
                node.params['has_ebest'] = True
                node.buildASMNode('ebest%d'%node.nodeid, 'ebest')
                node.asm_node['best%d'%node.nodeid].connect(node.asm_node['ebest%d'%node.nodeid], 'down', {'w': 0})
                node.asm_node['ebest%d'%node.nodeid].connect(node.asm_node['best%d'%node.nodeid], 'up', {'w': 0})
                node.asm_node['ebest%d'%node.nodeid].params['egp_cost'] = node.params['pref'] * self.max_length + node.params['egp_cost']
            else:
                node.params['has_ebest'] = False
        #print([(n.nodeid, n.asm_node) for n in self.node_list.values() if n.params['has_ebest']])
        for n1, n2 in self.connections:
            if self.node_list[n1].params['has_ebest']: self.node_list[n2].asm_node['best%d'%n2].connect(
                self.node_list[n1].asm_node['ebest%d'%n1], 'down', {
                    'w': self.node_list[n2].neighbors[n1]['params']['w']
                }
            )
            if self.node_list[n2].params['has_ebest']: self.node_list[n1].asm_node['best%d'%n1].connect(
                self.node_list[n2].asm_node['ebest%d'%n2], 'down', {
                    'w': self.node_list[n1].neighbors[n2]['params']['w']
                }
            )