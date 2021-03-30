import json
from topo.topo import Topo

class OSPF(Topo):
    def load_from_file(self, filename):
        with open(filename, 'r') as f:
            for line in f: 
                if line.startswith('#'): continue
                tokens = line.strip('\n').split('|')
                assert len(tokens) >= 3
                node1, node2, w = int(tokens[0]), int(tokens[1]), int(tokens[2])
                link = list(sorted([node1, node2]))
                node1_ins = self.add_node(node1)
                node2_ins = self.add_node(node2)
                node1_ins.connect(node2_ins, {'w': w})
                node2_ins.connect(node1_ins, {'w': w})
                self.link_list.append((link[0], link[1]))