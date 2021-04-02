from verifier.ismt_solver import iSMTSolver, Int, Bool

class iBGP(object):
    def __init__(self, topo, args, loader=None):
        self.topo = topo
        self.solver = iSMTSolver()
        self.isolver = iSMTSolver()
        self.ssolver = iSMTSolver()
        self.args = args
        if loader is not None:
            getattr(topo, loader)(args)

    def buildSMTConstraint(self):
        for node in self.topo.node_list.values():
            for asm_node in node.asm_node:
                if node.asm_node[asm_node].status != 'activate': continue
                constraints_or = []
                for dnode in node.asm_node[asm_node].dnode:
                    # calculate ranking 
                    if node.asm_node[asm_node].dnode[dnode]['node'].status != 'activate': continue
                    params = node.asm_node[asm_node].dnode[dnode]['params']
                    link = list(sorted([node.nodeid, node.asm_node[asm_node].dnode[dnode]['node'].node.nodeid]))
                    #ranking = params['egp_cost'] * self.topo.max_cost + (self.max_cost - params['w'])
                    # constraints -> larger than ranking
                    self.solver.setConstraintLib(
                        asm_node, Int('r_ranking_%s' % asm_node) >= Int('r_egp_cost_%s' % dnode) * self.topo.max_cost + (self.topo.max_cost - Int('w_%d_%d'%(link[0], link[1])))
                    )
                    self.solver.addParameter(Int('w_%d_%d'%(link[0], link[1])), params['w'])
                    # add dependencies 
                    self.solver.addDependency('%s' % asm_node, '%s' % dnode)
                    self.solver.addDependency('%s' % asm_node, 'w_%d_%d'%(link[0], link[1]))
                    if self.args.change_type == 'bad':
                        self.solver.add(self.solver.If(
                            Int('r_ranking_%s' % asm_node) == Int('r_egp_cost_%s' % dnode) * self.topo.max_cost + (self.topo.max_cost - Int('w_%d_%d'%(link[0], link[1]))),
                            self.solver.And([
                                Bool('d_%s_%s'%(asm_node, dnode)) == True, 
                                Bool('d_%s_w%d.%d'%(asm_node, link[0], link[1])) == True
                            ]),
                            self.solver.And([
                                Bool('d_%s_%s'%(asm_node, dnode)) == False,
                                Bool('d_%s_w%d.%d'%(asm_node, link[0], link[1])) == False
                            ])
                        ))
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
                    self.solver.setConstraintLib(asm_node, self.solver.And([
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
                if constraints_or != []: self.solver.setConstraintLib(asm_node, self.solver.Or(constraints_or))
                self.solver.addConstraintLib(asm_node)

    def incrementalModelGoodNews(self, model, change_node, egp_cost):
        def proc_unodes(current_node, unodes, constraints_or):
            for u in unodes.values(): 
                if u['node'].status != 'activate': continue
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
                if a.status != 'activate': continue
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

    def incrementalModelBadNews(self, model, change_node, egp_cost):
        def _need_recal(current_node, D, need_recal, traversed_node=[]):
            if current_node in need_recal: 
                for n in traversed_node: 
                    if n in need_recal: break
                    need_recal.append(n)
                return True
            if current_node not in D: return False
            for n in D[current_node]:
                if 'best' not in n: continue
                if _need_recal(n, D, need_recal): 
                    for n in traversed_node: 
                        if n in need_recal: break
                        need_recal.append(n)
                    return True
                return False
            return False

        need_recal = []
        # phase 1: extract dependencies
        D = {}
        for d in model.decls(): 
            if d.name().startswith('d_') and model[d]:
                tokens = d.name().strip('d_').split('_')
                assert len(tokens) == 2
                if tokens[0] not in D: D[tokens[0]] = [tokens[1].replace('.', '_')]
                else: D[tokens[0]].append(tokens[1].replace('.', '_'))
                if tokens[1] == change_node.name: need_recal.append(tokens[0])
        # phase 2, build constraints for variables; 
        for node in self.topo.node_list.values():
            for asm_node in node.asm_node:
                if node.asm_node[asm_node].status != 'activate': continue
                # if the node is changed node: recalculate 
                if asm_node == change_node.name:
                    self.isolver.add(self.solver.getConstraintLib(change_node.name))
                # if asm is known to be re-calculated
                elif asm_node in need_recal: 
                    self.isolver.add(self.solver.getConstraintLib(asm_node))
                # asm node not in D -> keep solution
                elif asm_node not in D: 
                    self.isolver.add(self.isolver.And([
                        Int('r_ranking_%s'%asm_node) == model[Int('r_ranking_%s'%asm_node)].as_long(),
                        Int('r_egp_cost_%s'%asm_node) == model[Int('r_egp_cost_%s'%asm_node)].as_long(),
                        Int('r_origin_%s'%asm_node) == -999999
                    ]))
                # traverse D
                elif _need_recal(asm_node, D, need_recal): 
                    self.isolver.add(self.solver.getConstraintLib(asm_node))
                else: 
                    self.isolver.add(self.isolver.And([
                        Int('r_ranking_%s'%asm_node) == model[Int('r_ranking_%s'%asm_node)].as_long(),
                        Int('r_egp_cost_%s'%asm_node) == model[Int('r_egp_cost_%s'%asm_node)].as_long(),
                        Int('r_origin_%s'%asm_node) == -999999
                    ]))
        # phase 3: rebuilt parameters
        self.isolver.params = self.solver.params
        self.isolver.rebuiltParamConstraints('egp_cost_%s'%change_node.name, egp_cost)

    def incrementalModel(self, model, change_node, egp_cost):
        #print(change_node)
        if egp_cost == change_node.params['egp_cost']: 
            return 
        elif egp_cost > change_node.params['egp_cost']:
            # good news
            assert self.args.change_type == 'good'
            return self.incrementalModelGoodNews(model, change_node, egp_cost)
        else: 
            assert self.args.change_type == 'bad'
            return self.incrementalModelBadNews(model, change_node, egp_cost)

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
            return self.solver.model()[key].as_long() == self.isolver.model()[key].as_long()
        for n in self.topo.node_list.values():
            for asm_node in n.asm_node.values():
                if asm_node.status != 'activate': continue
                try:
                    assert verify_value(Int('r_egp_cost_%s'%asm_node.name))
                    assert verify_value(Int('r_ranking_%s'%asm_node.name))
                except: 
                    #pass
                    print('verify failed at node ', asm_node.name, ':')
                    print('-- egp_cost', self.solver.model()[Int('r_egp_cost_%s'%asm_node.name)].as_long(), self.isolver.model()[Int('r_egp_cost_%s'%asm_node.name)].as_long())
                    print('-- ranking', self.solver.model()[Int('r_ranking_%s'%asm_node.name)].as_long(), self.isolver.model()[Int('r_ranking_%s'%asm_node.name)].as_long())
                