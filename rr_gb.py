import sys
import json
import random
from verifier.models import iBGP, RouteReflector
from topo import BGPTopo
import argparse
import time

def bgp(args):
    v = iBGP(BGPTopo(args), args, 'build_from_abstraction')
    v.buildSMTConstraint()
    print(v.topo.args)
    print('=== Initial Experiment ===')
    t1 = time.time()
    print(v.solver.check())
    t2 = time.time()
    #print(v.solver.param_dependencies)
    #print(v.solver.solver)
    model = v.solver.model()
    #print(model)
    ebest_nodes = [n.asm_node['ebest%s'%n.nodeid] for n in v.topo.node_list.values() if n.params['has_ebest']]
    change_node = ebest_nodes[random.randint(0, len(ebest_nodes) - 1)]
    v.buildStaticSolver(model, change_node, args.new_cost)
    #print('=== Static Analysis ===')
    #t7 = time.time()
    #print(v.ssolver.check())
    #t8 = time.time()
    #print(change_node.name)
    print('=== Incremental Solving ===')
    v.incrementalModel(model, change_node, args.new_cost)
    t3 = time.time()
    print(v.isolver.check())
    #print(v.isolver.solver)
    t4 = time.time()
    #print(v.isolver.model())
    print('=== Using incremental Z3 ===')
    v.iZ3Build(change_node, args.new_cost)
    t5 = time.time()
    print(v.solver.check())
    t6 = time.time()
    #print(v.solver.solver)
    #print(v.solver.model())
    v.verify()
    print(t2-t1, t4-t3, t6-t5, (t6-t5)/(t4-t3))

    with open('rr_good_bad.csv', 'a') as f:
        f.write('{},{},{},{},{},{}\n'.format(
            len(v.topo.node_list), t2-t1, t4-t3, t6-t5, (t6-t5)/(t4-t3), args.change_type
        ))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='iASM')
    parser.add_argument('-t', '--topo', help='Topology file')
    parser.add_argument('-a', '--announcement', help='BGP Announcement files, required for BGP topologies')
    parser.add_argument('-c', '--configuration', help='BGP configurations')
    parser.add_argument('-n', '--change-type', choices=['good', 'bad'], help='The type of changes in network.')
    parser.add_argument('-p', '--new-cost', type=int, help='New BGP cost')
    args = parser.parse_args()
    bgp(args)