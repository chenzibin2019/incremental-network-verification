from asm.asm_node import ASMNode
class Node(object):
    def __init__(self, nodeid: int):
        self.nodeid = nodeid
        self.asm_node = {}
        self.neighbors = {}     # neighbors -> id: {'node': node, 'params': {key: val}}
        self.params = {}

    def connect(self, neighbor, params={}):
        if neighbor.nodeid not in self.neighbors: self.neighbors[neighbor.nodeid] = {'node': neighbor, 'params': params}

    def buildASMNode(self, name, atype):
        if name not in self.asm_node: self.asm_node[name] = ASMNode(name, self, atype)
        return self