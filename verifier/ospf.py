import time
from z3 import Int, sat
from verifier.verifier import Verifier
from verifier.ismt_solver import iSMTSolver

class OSPF(Verifier):
    def __init__(self, topo, args, loader=None):
        super(OSPF, self).__init__(topo, args, loader)
        self.isolver = iSMTSolver()

    def buildParams(self, force_key=None, force_value=None):
        print(force_key)
        for n in self.topo.node_list.values(): 
            self.solver.addParameter(Int('r_%d_prev'%n.nodeid), 999999999999)
            for nb in n.neighbors:
                if n.nodeid <= nb: 
                    if force_key is not None and nb in force_key and n.nodeid in force_key: 
                        self.solver.addParameter(Int('w_%d_%d'%(n.nodeid, nb)), force_value)
                    else: 
                        self.solver.addParameter(Int('w_%d_%d'%(n.nodeid, nb)), n.neighbors[nb]['params']['w'])
        return self

    def buildSMTConstraint(self):
        for n in self.topo.node_list.values():
            constraint_or = [self.solver.And([
                Int('r_%d'%n.nodeid) == Int('r_%d_prev'%n.nodeid),
                Int('r_next_hop_%d'%n.nodeid) == Int('r_next_hop_%d_prev'%n.nodeid),
            ])]
            self.solver.constraint_prep.append(Int('r_%d'%n.nodeid) <= Int('r_%d_prev'%n.nodeid))
            for nb in n.neighbors: 
                link = list(sorted([n.nodeid, nb]))
                self.solver.constraint_prep.append(Int('r_%d'%n.nodeid) <= Int('r_%d_prev'%nb) + Int('w_%d_%d'%(link[0], link[1])))
                constraint_or.append(self.solver.And([
                    Int('r_%d'%n.nodeid) == Int('r_%d_prev'%nb) + Int('w_%d_%d'%(link[0], link[1])),
                    Int('r_next_hop_%d'%n.nodeid) == nb
                ]))
            self.solver.constraint_prep.append(self.solver.Or(constraint_or))

    def recurrentSolving(self, dest):
        model = {}
        for n in self.topo.node_list.values():
            if n.nodeid == dest: 
                model[Int('r_%d'%n.nodeid)] = 0
                model[Int('r_next_hop_%d'%n.nodeid)] = 0
            else: 
                model[Int('r_%d'%n.nodeid)] = 999999999999
                model[Int('r_next_hop_%d'%n.nodeid)] = -1
        return self.SMTSolving(model)

    def incrementalModel(self, prev_model, changed_link, new_cost):
        # changed link should be a list containing two ids. 
        # phase 1: 
        assert len(changed_link) == 2
        assert changed_link[0] < changed_link[1]
        # for first node
        prev_cost_n1 = prev_model[Int('r_%d'%changed_link[0])].as_long()
        new_cost_n1 = prev_model[Int('r_%d'%changed_link[1])].as_long() + prev_model[Int('w_%d_%d'%(changed_link[0], changed_link[1]))]
        self.isolver.add(Int('r_%d'%changed_link[0]) <= prev_cost_n1)
        self.isolver.add(Int('r_%d'%changed_link[0]) <= new_cost_n1)
        self.isolver.add(self.isolver.Or([
            self.isolver.And([
                Int('r_%d'%changed_link[0]) == prev_cost_n1, 
                Int('r_next_hop_%d'%changed_link[0]) == prev_model[Int('r_next_hop_%d'%changed_link[0])].as_long()
            ]), self.isolver.And([
                Int('r_%d'%changed_link[0]) == prev_cost_n1, 
                Int('r_next_hop_%d'%changed_link[0]) == changed_link[1]
            ])
        ]))
        prev_cost_n2 = prev_model[Int('r_%d'%changed_link[1])].as_long()
        new_cost_n2 = prev_model[Int('r_%d'%changed_link[0])].as_long() + prev_model[Int('w_%d_%d'%(changed_link[0], changed_link[1]))]
        self.isolver.add(Int('r_%d'%changed_link[1]) <= prev_cost_n2)
        self.isolver.add(Int('r_%d'%changed_link[1]) <= new_cost_n2)
        self.isolver.add(self.isolver.Or([
            self.isolver.And([
                Int('r_%d'%changed_link[1]) == prev_cost_n2, 
                Int('r_next_hop_%d'%changed_link[1]) == prev_model[Int('r_next_hop_%d'%changed_link[1])].as_long()
            ]), self.isolver.And([
                Int('r_%d'%changed_link[1]) == prev_cost_n2, 
                Int('r_next_hop_%d'%changed_link[1]) == changed_link[0]
            ])
        ]))
        assert self.isolver.check()
        model = self.isolver.model()
        return self.incrementalSolving(prev_model, changed_link, new_cost, changed_link, model)

    def incrementalSolving(self, prev_model, changed_link, new_cost, in_model, last_model, t=0, i=1):
        self.isolver.reset()
        constraint_or = {}
        next_in_model = [n for n in in_model]
        for n in in_model:
            for nb in self.topo.node_list[n].neighbors: 
                link = list(sorted([n, nb]))
                if n in changed_link and nb in changed_link: w = new_cost
                else: w = prev_model[Int('w_%d_%d'%(link[0], link[1]))].as_long()
                if nb not in constraint_or:
                    self.isolver.add(Int('r_%d'%nb) <= Int('r_%d_prev'%nb))
                    constraint_or[nb] = [self.isolver.And([
                        Int('r_%d'%nb) == Int('r_%d_prev'%nb),
                        Int('r_next_hop_%d'%nb) == Int('r_next_hop_%d_prev'%nb)
                    ])]
                self.isolver.add(Int('r_%d'%nb) <= Int('r_%d_prev'%n) + w)
                constraint_or[nb].append(self.isolver.And([
                    Int('r_%d'%nb) == Int('r_%d_prev'%n) + w,
                    Int('r_next_hop_%d'%nb) == Int('r_next_hop_%d_prev'%n)
                ]))
                
                #if nb in in_model: 
                #    self.isolver.addParameter(Int('r_%d_prev'%nb), last_model[Int('r_%d'%nb)].as_long())
                #    self.isolver.addParameter(Int('r_next_hop_%d_prev'%nb), last_model[Int('r_next_hop_%d'%nb)].as_long())
                if nb not in next_in_model: 
                    self.isolver.addParameter(Int('r_%d_prev'%nb), prev_model[Int('r_%d'%nb)].as_long())
                    self.isolver.addParameter(Int('r_next_hop_%d_prev'%nb), prev_model[Int('r_next_hop_%d'%nb)].as_long())
                    next_in_model.append(nb)
            
            self.isolver.addParameter(Int('r_%d_prev'%n), last_model[Int('r_%d'%n)].as_long())
            self.isolver.addParameter(Int('r_next_hop_%d_prev'%n), last_model[Int('r_next_hop_%d'%n)].as_long())
        
        for o in constraint_or.values(): 
            self.isolver.add(self.isolver.Or(o))
        t1 = time.time()
        assert self.isolver.check() == sat
        t2 = time.time()
        model = self.isolver.model()

        need_continue = False
        for n in next_in_model: 
            if model[Int('r_%d'%n)].as_long() != model[Int('r_%d_prev'%n)].as_long(): 
                need_continue = True
        t += (t2 -t1)
        if not need_continue: 
            return t, model, i
        return self.incrementalSolving(prev_model, changed_link, new_cost, next_in_model, model, t, i+1)

    def SMTSolving(self, model):
        t = 0.0
        itr = 0
        while True:
            self.solver.clear()
            for d in model: 
                name = d.__str__()
                if name.startswith('r_') and not name.endswith('_prev'): 
                    self.solver.params[Int('%s_prev' % d)] = model[d]
            self.solver.rebuiltParamConstraints()
            self.solver.add(self.solver.And(self.solver.constraint_prep))
            t1 = time.time()
            assert self.solver.check() == sat
            t2 = time.time()
            itr += 1
            print(itr, end='\r')
            t += (t2 - t1)
            need_continue = False
            model = self.solver.model()
            for n in self.topo.node_list:
                if not model[Int('r_%d_prev'%n)].as_long() == model[Int('r_%d'%n)].as_long(): need_continue = True
            if not need_continue: break
        print('')
        return t, model, itr
        
    def iZ3Build(self, model, changed_link, new_cost):
        self.solver.solver.pop()
        self.solver.rebuiltParamConstraints('w_%d_%d'%(changed_link[0], changed_link[1]), new_cost)
        assert self.solver.check() == sat
        return self.SMTSolving(self.solver.model())

    def iZ3Solving(self, model):
        t = 0.0
        itr = 0
        while True:
            #self.solver.clear()
            for d in model: 
                name = d.__str__()
                if name.startswith('r_') and not name.endswith('_prev'): 
                    self.solver.params[Int('%s_prev' % d)] = model[d]
            self.solver.rebuiltParamConstraints()
            #self.solver.add(self.solver.And(self.solver.constraint_prep))
            self.solver.solver.pop()
            t1 = time.time()
            assert self.solver.check() == sat
            t2 = time.time()
            itr += 1
            print(itr, end='\r')
            t += (t2 - t1)
            need_continue = False
            model = self.solver.model()
            for n in self.topo.node_list:
                if not model[Int('r_%d_prev'%n)].as_long() == model[Int('r_%d'%n)].as_long(): need_continue = True
            if not need_continue: break
        print('')
        return t, model, itr
    
    def verify(self, asm, iasm, iz3):
        for n in self.topo.node_list:
            iasm_sol = iasm[Int('r_%d'%n)].as_long() if iasm[Int('r_%d'%n)] is not None else asm[Int('r_%d'%n)].as_long()
            iz3_sol = iz3[Int('r_%d'%n)].as_long()
            assert iasm_sol == iz3_sol

    def verify_static(self, model, imodel):
        for n in self.topo.node_list:
            iz3_sol = imodel[Int('r_%d'%n)].as_long()
            assert model[Int('r_%d'%n)].as_long() == iz3_sol
        print('passed modeled solution checking')