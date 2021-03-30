from verifier.ismt_solver import iSMTSolver, Int

class iBGP(object):
    def __init__(self, topo, args, loader=None):
        self.topo = topo
        self.solver = iSMTSolver()
        self.isolver = iSMTSolver()
        self.ssolver = iSMTSolver()
        if loader is not None:
            getattr(topo, loader)(args)

    def buildSMTConstraint(self):
        for node in self.topo.node_list.values():
            for asm_node in node.asm_node:
                constraints_or = []
                for dnode in node.asm_node[asm_node].dnode:
                    # calculate ranking 
                    params = node.asm_node[asm_node].dnode[dnode]['params']
                    link = list(sorted([node.nodeid, node.asm_node[asm_node].dnode[dnode]['node'].node.nodeid]))
                    #ranking = params['egp_cost'] * self.topo.max_cost + (self.max_cost - params['w'])
                    # constraints -> larger than ranking
                    self.solver.add(
                        Int('r_ranking_%s' % asm_node) >= Int('r_egp_cost_%s' % dnode) * self.topo.max_cost + (self.topo.max_cost - Int('w_%d_%d'%(link[0], link[1])))
                    )
                    self.solver.addParameter(Int('w_%d_%d'%(link[0], link[1])), params['w'])
                    # add dependencies 
                    self.solver.addDependency('r_%s' % asm_node, 'r_%s' % dnode)
                    self.solver.addDependency('r_%s' % asm_node, 'w_%d_%d'%(link[0], link[1]))
                    # add or constraints
                    constraints_or.append(self.solver.And([
                        Int('r_egp_cost_%s' % asm_node) == Int('r_egp_cost_%s' % dnode),
                        Int('r_ranking_%s' % asm_node) == Int('r_egp_cost_%s' % dnode) * self.topo.max_cost + (self.topo.max_cost - Int('w_%d_%d'%(link[0], link[1]))),
                        Int('r_origin_%s'% asm_node) == -1 * node.asm_node[asm_node].dnode[dnode]['node'].node.nodeid
                    ]))
                    #print(asm_node, node.asm_node[asm_node].type)
                if node.asm_node[asm_node].type == 'ebest': 
                    # if the node is a ebest node with eBGP sessions:
                    # additional constraints following eBGP announcements: 
                    #rank_e = node.asm_node[asm_node].params['egp_cost'] * self.topo.max_cost + self.topo.max_cost
                    self.solver.add(self.solver.And([
                        Int('r_ranking_%s'%asm_node) >= Int('egp_cost_%s'%asm_node) * self.topo.max_cost + self.topo.max_cost,
                    ]))
                    #self.solver.addDependency('r_%s' % asm_node, 'e')
                    #self.solver.addParameter(Int('e_rank_%d'%node.asm_node[asm_node].node.nodeid), rank_e)
                    self.solver.addParameter(Int('egp_cost_%s'%asm_node), node.asm_node[asm_node].params['egp_cost'])
                    constraints_or.append(self.solver.And([
                        Int('r_ranking_%s'%asm_node) == Int('egp_cost_%s'%asm_node) * self.topo.max_cost + self.topo.max_cost,
                        Int('r_egp_cost_%s'%asm_node) == Int('egp_cost_%s'%asm_node),
                        Int('r_origin_%s'% asm_node) == 0
                    ]))
                #print(asm_node, node.asm_node[asm_node].dnode, constraints_or)
                self.solver.add(self.solver.Or(constraints_or))

    def incrementalModel(self, model, change_node, egp_cost):
        def proc_unodes(current_node, unodes, constraints_or):
            for u in unodes.values(): 
                constraints_or[u['node'].name].append(self.isolver.And([
                    Int('r_ranking_%s'%(u['node'].name)) == Int('r_egp_cost_%s' % current_node.name) * self.topo.max_cost + (self.topo.max_cost - u['params']['w']),
                    Int('r_egp_cost_%s'%u['node'].name) == Int('r_egp_cost_%s' % current_node.name),
                    Int('r_origin_%s'%u['node'].name) == -1 * current_node.node.nodeid
                ]))
                self.isolver.add(Int('r_ranking_%s'%(u['node'].name)) >= Int('r_egp_cost_%s' % current_node.name) * self.topo.max_cost + (self.topo.max_cost - u['params']['w']))
                new_unodes = u['node'].unode
                proc_unodes(u['node'], new_unodes, constraints_or)

        #phase 1: all nodes has its origin solution. 
        constraints_or = {}
        for node in self.topo.node_list.values(): 
            for a in node.asm_node.values(): 
                constraints_or[a.name] = [self.isolver.And([
                    Int('r_ranking_%s'%a.name) == model[Int('r_ranking_%s'%a.name)],
                    Int('r_egp_cost_%s'%a.name) == model[Int('r_egp_cost_%s'%a.name)],
                    Int('r_origin_%s'%a.name) == -999999
                ])]

        #phase 2: from changed node, search up nodes, add incoming edges. 
        # update self
        constraints_or[change_node.name].append(self.isolver.And([
            Int('r_ranking_%s'%change_node.name) == egp_cost * self.topo.max_cost + self.topo.max_cost,
            Int('r_egp_cost_%s'%change_node.name) == egp_cost,
            Int('r_origin_%s'%change_node.name) == 999999999
        ]))
        self.isolver.add(Int('r_ranking_%s'%change_node.name) >= egp_cost * self.topo.max_cost + self.topo.max_cost)
        proc_unodes(change_node, change_node.unode, constraints_or)
        #phase3: add constraints or in
        for o in constraints_or:
            self.isolver.add(self.isolver.Or(constraints_or[o]))
            #print(o, constraints_or[o])

    def iZ3Build(self, change_node, egp_cost):
        self.solver.solver.pop()
        self.solver.rebuiltParamConstraints('egp_cost_%s'%change_node.name, egp_cost)
        return self

    def buildStaticSolver(self, model, change_node, egp_cost):
        for node in self.topo.node_list.values():
            for asm_node in node.asm_node:
                constraints_or = []
                for dnode in node.asm_node[asm_node].dnode:
                    # calculate ranking 
                    params = node.asm_node[asm_node].dnode[dnode]['params']
                    link = list(sorted([node.nodeid, node.asm_node[asm_node].dnode[dnode]['node'].node.nodeid]))
                    #ranking = params['egp_cost'] * self.topo.max_cost + (self.max_cost - params['w'])
                    # constraints -> larger than ranking
                    self.ssolver.add(
                        Int('r_ranking_%s' % asm_node) >= Int('r_egp_cost_%s' % dnode) * self.topo.max_cost + (self.topo.max_cost - Int('w_%d_%d'%(link[0], link[1])))
                    )
                    self.ssolver.addParameter(Int('w_%d_%d'%(link[0], link[1])), params['w'])
                    # add dependencies 
                    self.ssolver.addDependency('r_%s' % asm_node, 'r_%s' % dnode)
                    self.ssolver.addDependency('r_%s' % asm_node, 'w_%d_%d'%(link[0], link[1]))
                    # add or constraints
                    constraints_or.append(self.ssolver.And([
                        Int('r_egp_cost_%s' % asm_node) == Int('r_egp_cost_%s' % dnode),
                        Int('r_ranking_%s' % asm_node) == Int('r_egp_cost_%s' % dnode) * self.topo.max_cost + (self.topo.max_cost - Int('w_%d_%d'%(link[0], link[1]))),
                        Int('r_origin_%s'% asm_node) == -1 * node.asm_node[asm_node].dnode[dnode]['node'].node.nodeid
                    ]))
                    #print(asm_node, node.asm_node[asm_node].type)
                if node.asm_node[asm_node].type == 'ebest': 
                    if node.asm_node[asm_node].name == change_node.name:
                        # if the node is a ebest node with eBGP sessions:
                        # additional constraints following eBGP announcements: 
                        #rank_e = node.asm_node[asm_node].params['egp_cost'] * self.topo.max_cost + self.topo.max_cost
                        self.ssolver.add(self.ssolver.And([
                            Int('r_ranking_%s'%asm_node) >= Int('egp_cost_%s'%asm_node) * self.topo.max_cost + self.topo.max_cost,
                        ]))
                        #self.ssolver.addDependency('r_%s' % asm_node, 'e')
                        #self.ssolver.addParameter(Int('e_rank_%d'%node.asm_node[asm_node].node.nodeid), rank_e)
                        self.ssolver.addParameter(Int('egp_cost_%s'%asm_node), egp_cost)
                        constraints_or.append(self.ssolver.And([
                            Int('r_ranking_%s'%asm_node) == Int('egp_cost_%s'%asm_node) * self.topo.max_cost + self.topo.max_cost,
                            Int('r_egp_cost_%s'%asm_node) == Int('egp_cost_%s'%asm_node),
                            Int('r_origin_%s'% asm_node) == 0
                        ]))
                    else: 
                        self.ssolver.add(self.ssolver.And([
                            Int('r_ranking_%s'%asm_node) == model[Int('r_ranking_%s'%asm_node)].as_long(),
                            Int('r_egp_cost_%s'%asm_node) == model[Int('r_egp_cost_%s'%asm_node)].as_long(),
                        ]))
                #print(asm_node, node.asm_node[asm_node].dnode, constraints_or)
                #print(asm_node)
                if constraints_or != []: self.ssolver.add(self.ssolver.Or(constraints_or))

    def verify(self):
        def verify_value(key):
            return self.solver.model()[key] == self.ssolver.model()[key]
        for n in self.topo.node_list.values():
            for asm_node in n.asm_node.values():
                assert verify_value(Int('r_egp_cost_%s'%asm_node.name))
                assert verify_value(Int('r_ranking_%s'%asm_node.name))
                