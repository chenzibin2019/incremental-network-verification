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
        self.max_egp_cost = 0

    def build_from_abstraction(self, args):
        self.load_from_file(args.topo)
        self.load_announcements(args.announcement)
        self.load_configuration(args.configuration)
        self.build_asm()
        self.trimASMNode()

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
            max_length = 10
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
                if self.node_list[nodeid].params['egp_cost'] > self.max_egp_cost: 
                    self.max_egp_cost = self.node_list[nodeid].params['egp_cost']
            # record max_length
            self.max_length = max_length

    def load_configuration(self, filename):
        with open(filename, 'r') as f:
            configuration = json.load(f)
            for p in configuration:
                if int(p) in self.node_list: 
                    self.node_list[int(p)].params['conf'] = configuration[p]
                    self.node_list[int(p)].params['route-reflector-client'] = []
                    if "external" in configuration[p]: 
                        self.node_list[int(p)].params['has_configuration'] = True
                        self.node_list[int(p)].params['pref'] = configuration[p]['external']['pref']
                    for bp in configuration[p]: 
                        if 'route-reflector-client' in configuration[p][bp] and configuration[p][bp]['route-reflector-client']:
                            self.node_list[int(p)].params['has_route_reflector_client'] = True
                            self.node_list[int(p)].params['route-reflector-client'].append(int(bp))

    def build_asm(self):
        for node in self.node_list.values():
            node.buildASMNode('best%d' % node.nodeid, 'best')
            if node.params['has_announcement'] and node.params['has_configuration']: 
                node.params['has_ebest'] = True
                node.buildASMNode('ebest%d'%node.nodeid, 'ebest')
                node.asm_node['best%d'%node.nodeid].connect(node.asm_node['ebest%d'%node.nodeid], 'down', {'w': 0})
                node.asm_node['ebest%d'%node.nodeid].connect(node.asm_node['best%d'%node.nodeid], 'up', {'w': 0})
                node.asm_node['ebest%d'%node.nodeid].params['egp_cost'] = node.params['pref'] * self.max_egp_cost + node.params['egp_cost']
            else:
                node.params['has_ebest'] = False
            if 'has_route_reflector_client' in node.params and node.params['has_route_reflector_client']:
                node.params['has_cbest'] = True
                node.buildASMNode('cbest%d' % node.nodeid, 'cbest')
                node.asm_node['best%d'%node.nodeid].connect(node.asm_node['cbest%d'%node.nodeid], 'down', {'w': 0})
                node.asm_node['cbest%d'%node.nodeid].connect(node.asm_node['best%d'%node.nodeid], 'up', {'w': 0})
            else: 
                node.params['has_cbest'] = False
            assert not (node.params['has_ebest'] and node.params['has_cbest'])
        #print([(n.nodeid, n.asm_node) for n in self.node_list.values() if n.params['has_ebest']])
        for n1, n2 in self.connections:
            w = self.node_list[n2].neighbors[n1]['params']['w']
            if n2 in self.node_list[n1].params['route-reflector-client']:
                assert ('router-reflector-client' not in self.node_list[n2].params 
                    or n1 not in self.node_list[n2].params['router-reflector-client'])
                if self.node_list[n2].params['has_ebest']:
                    self.node_list[n1].asm_node['cbest%d'%n1].connect(self.node_list[n2].asm_node['ebest%d'%n2], 'down', {'w': w})
                    self.node_list[n2].asm_node['ebest%d'%n2].connect(self.node_list[n1].asm_node['cbest%d'%n1], 'up', {'w': w})
                self.node_list[n2].asm_node['best%d'%n2].connect(self.node_list[n1].asm_node['best%d'%n1], 'down', {'w': w})
                self.node_list[n1].asm_node['best%d'%n1].connect(self.node_list[n2].asm_node['best%d'%n2], 'up', {'w': w})
            elif n1 in self.node_list[n2].params['route-reflector-client']:
                if self.node_list[n1].params['has_ebest']:
                    self.node_list[n2].asm_node['cbest%d'%n2].connect(self.node_list[n1].asm_node['ebest%d'%n1], 'down', {'w': w})
                    self.node_list[n1].asm_node['ebest%d'%n1].connect(self.node_list[n2].asm_node['cbest%d'%n2], 'up', {'w': w})
                self.node_list[n1].asm_node['best%d'%n1].connect(self.node_list[n2].asm_node['best%d'%n2], 'down', {'w': w})
                self.node_list[n2].asm_node['best%d'%n2].connect(self.node_list[n1].asm_node['best%d'%n1], 'up', {'w': w})
            else:
                if self.node_list[n1].params['has_ebest']: 
                    self.node_list[n2].asm_node['best%d'%n2].connect(self.node_list[n1].asm_node['ebest%d'%n1], 'down', {'w': w})
                    self.node_list[n1].asm_node['ebest%d'%n1].connect(self.node_list[n2].asm_node['best%d'%n2], 'up', {'w': w})
                elif self.node_list[n1].params['has_cbest']: 
                    self.node_list[n2].asm_node['best%d'%n2].connect(self.node_list[n1].asm_node['cbest%d'%n1], 'down', {'w': w})
                    self.node_list[n1].asm_node['cbest%d'%n1].connect(self.node_list[n2].asm_node['best%d'%n2], 'up', {'w': w})
                if self.node_list[n2].params['has_ebest']: 
                    self.node_list[n1].asm_node['best%d'%n1].connect(self.node_list[n2].asm_node['ebest%d'%n2], 'down', {'w': w})
                    self.node_list[n2].asm_node['ebest%d'%n2].connect(self.node_list[n1].asm_node['best%d'%n1], 'up', {'w': w})
                if self.node_list[n2].params['has_cbest']: 
                    self.node_list[n1].asm_node['best%d'%n1].connect(self.node_list[n2].asm_node['cbest%d'%n2], 'down', {'w': w})
                    self.node_list[n2].asm_node['cbest%d'%n2].connect(self.node_list[n1].asm_node['best%d'%n1], 'up', {'w': w})

    def trimASMNode(self):
        def _do_trim(nodes):
            for n in nodes: 
                n.status = 'activate'
                _do_trim([u['node'] for u in n.unode.values()])
        _do_trim([n.asm_node['ebest%d'%n.nodeid] for n in self.node_list.values() if n.params['has_ebest']])