import sys
import json
import random
from verifier.models import OSPF
from topo import OSPFTopo
import argparse
import time

def ospf(args):
    v = OSPF(OSPFTopo(), args.topo, 'load_from_file')
    v.buildParams().buildSMTConstraint()
    print('verification')
    t1, model1, itr1 = v.recurrentSolving(1)
    change_node = random.choice(v.topo.link_list)
    print(change_node)
    print('incremental')
    t2, model2, itr2 = v.incrementalModel(model1, change_node, 0)
    print('iz3')
    t3, model3, itr3 = v.iZ3Build(model1, change_node, 0)
    vt = OSPF(OSPFTopo(), args.topo, 'load_from_file')
    vt.buildParams(force_key=change_node, force_value=0).buildSMTConstraint()
    t4, model4, itr4 = vt.recurrentSolving(1)
    v.verify_static(model4, model3)
    print(t1, itr1, t2, itr2, t3)
    v.verify(model1, model2, model3)
    with open('ospf_result3.csv', 'a') as f:
        f.write('{},{},{},{},{},{},{}\n'.format(
            args.topo, t1, t2, t3, t3/t2, itr2, itr3
        ))
        f.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='iASM')
    parser.add_argument('-t', '--topo', help='Topology file')
    args = parser.parse_args()
    ospf(args)