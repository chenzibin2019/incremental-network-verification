import sys
import json
import random
from verifier.models import iBGP
from topo import BGPTopo
import argparse
import time

def bgp(args):
    v = iBGP(BGPTopo(), args, 'build_from_abstraction')
    v.buildSMTConstraint()
    t1 = time.time()
    print(v.solver.check())
    t2 = time.time()
    #print(v.solver.param_dependencies)
    #print(v.solver.solver)
    model = v.solver.model()
    #print(model)
    ebest_node = [n.asm_node['ebest%s'%n.nodeid] for n in v.topo.node_list.values() if n.params['has_ebest']]
    v.incrementalModel(model, ebest_node[random.randint(0, len(ebest_node) - 1)] , 10)
    t3 = time.time()
    print(v.isolver.check())
    t4 = time.time()
    #print(v.isolver.model())
    #print(v.topo.node_list[2].params)
    #print(v.topo.node_list[2].asm_node)
    print(t2 - t1, t4 - t3)
    
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='iASM')
    parser.add_argument('-t', '--topo', help='Topology file')
    parser.add_argument('-a', '--announcement', help='BGP Announcement files, required for BGP topologies')
    parser.add_argument('-p', '--preference', help='Local preference specification')
    args = parser.parse_args()
    bgp(args)