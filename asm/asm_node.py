
class ASMNode(object):
    def __init__(self, name, node, atype):
        self.name = name
        self.node = node
        self.dnode = {}     # u/d-node-> name: {'node': node, 'params': {key: val}}
        self.unode = {}
        self.params = {}
        self.status = 'deactivate'  # to prone nodes, valid options: 'deactivate', 'pendings', 'activate'
        self.type = atype

    def connect(self, asm_node, direction='up', params={}):
        if direction == 'up': node_set = self.unode
        elif direction == 'down': node_set = self.dnode
        else: raise ValueError('Invalid direction %s at %s' % (direction, self.name))
        if asm_node.name not in node_set: node_set[asm_node.name] = {'node': asm_node, 'params': params}
        

