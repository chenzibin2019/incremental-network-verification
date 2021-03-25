from topo.node import Node

class Topo(object):
    def __init__(self):
        self.node_list = {}

    def add_node(self, node):
        if isinstance(node, int): 
            if node not in self.node_list: 
                self.node_list[node] = Node(node)
            return self.node_list[node]
        else:
            if node.nodeid not in self.node_lst: 
                self.node_list[node.nodeid] = node
            return node
