# IOT - Routing simulator
# Group 7
# Retransmission test of a simpy node network
# The code is originally based off of examples/aodv.py

import random
from typing import Sequence
from simpy.events import Timeout
import wsnsimpy.wsnsimpy_tk as wsp
from anytree import Node, RenderTree, find_by_attr, AsciiStyle, find
import threading
from tools import cprint
import re
import json

ROOT = 6
# DEST   = 6
debug_cnt = 0
delayOn = True
pPackageLoss = 0.30  # Packet loss probability
trickleTimeInit = 1.5
retransmissions = 5
grid = 7 # resulting in grid x grid number of nodes
random.seed(5)

from enum import Enum


class RPMType(Enum):
    DIO = 1
    DAO = 2
    DIS = 3
    DATA = 4
    ACK = 5


###########################################################
def delay():
    if delayOn:
        return random.uniform(.2, .8)
    else:
        return 0


class RPLMessage:
    def __init__(self, type=RPMType.DIO, src="", dst="", data=0, path=[], sequence=None, version=1) -> None:
        self.type = RPMType(type)
        self.src = src           # source of message
        self.dst = dst           # destination of message
        self.sequence = sequence # Sequence number of message, used for ack
        self.data = data         # message Data
        self.path = path         # Node path to dst as a list of nodes.
        self.version = version   # DODAG version


###########################################################
class MyNode(wsp.Node):
    tx_range = 140
    version = 0
    trickleTime = trickleTimeInit
    trickleCount = 1
    rank = 0
    sequence_count = 0
    sender = 0
    last_seq = 0
    last_node = 0
    ###################
    def init(self):
        super().init()
        self.prev = None
        self.rank = 0
        self.ack = [False] * (grid*grid)
        self.sequences = []

    ###################
    # Startup command for each node
    # sets color of ROOT and destination node.
    def run(self):
        if self.id is ROOT:
            self.root = Node(str(self.id))
            self.prev = 0
            self.paths = []
            self.scene.nodecolor(self.id, 1, 0, 1)
            self.scene.nodewidth(self.id, 2)
            yield self.timeout(0)
            self.version = 1  # set root node version to 1 to enable it to send trickle messages
            

        # elif self.id is DEST:
        #    self.scene.nodecolor(self.id,1,0,0)
        #    self.scene.nodewidth(self.id,2)
        else:
            self.scene.nodecolor(self.id, .7, .7, .7)

        while True:  # Trickle algorithm

            if self.version > 0:
                self.send_DIO()

                # print(f"Trickle. Version: {self.version}, TrickleTime: {self.trickleTime}, Delay: {delay()}, id: {self.id}, tricklecount: {self.trickleCount} ")
                self.trickleCount += 1

            yield self.timeout(self.trickleTime)
            self.trickleTime = pow(self.trickleCount, 1.2) * (
                        delay() + 0.8)  # Time between trickles increase exponentially

    ###################
    def send_DIO(self):
        rplMsg = RPLMessage(type=RPMType.DIO, src=self.id, data=self.rank)
        self.send(wsp.BROADCAST_ADDR, msg=rplMsg)
        self.sequence_count = self.sequence_count + 1

    def send_DAO(self, rplMsg=None):
        if rplMsg is None:
            list = [self.id]
            rplMsg = RPLMessage(type=RPMType.DAO, src=self.id, path=list, sequence="{}.{}".format(self.id,self.sequence_count))
        elif self.id not in rplMsg.path:
            rplMsg.path.append(self.id)
        self.send(self.prev, msg=rplMsg)
        

    def send_DIS(self):
        rplMsg = RPLMessage(type=RPMType.DIS, src=self.id, data=self.rank)
        self.send(wsp.BROADCAST_ADDR, msg=rplMsg)
        

    ###################
    def send_data(self, rplMsg):
        if not rplMsg.sequence:
            print("seq set")
            rplMsg.sequence="{}.{}".format(self.id,self.sequence_count)
        if rplMsg.src is ROOT:
            if self.id is ROOT:  # if root set path to in rplmsg
                rplMsg.path = self.path_to_node(rplMsg.dst)
            self.send(rplMsg.path[self.rank + 1], msg=rplMsg)
        else:
            self.send(self.prev, msg=rplMsg)

    def send_ack(self, ackdst = None):
        msg = RPLMessage(type=RPMType.ACK, src=self.id, dst=ackdst)
        self.send(ackdst, msg=msg)

    ###################
    def on_receive(self, sender, msg, **kwargs):
        if random.random() < pPackageLoss:  # Packet loss
            pass
        else:
            self.sender = sender
            if msg.type == RPMType.DIO:  # root to nodes
                # Objective function. 
                # 1 Change parrent if trickle node has lower rank. 
                # 2 Set parrent if not set
                # 3 check if Dodag version in MSG is lower than current DODAG. this overrules
                if (msg.data + 1 < self.rank and msg.src is not self.prev) or self.version < msg.version:
                    if self.prev is not None:
                        sim.scene.dellink(self.prev, self.id, "parent")
                        cprint("node {} want to change from node {} to {}".format(str(self.id), self.prev,msg.src),"FAIL")

                    self.version = msg.version
                    self.rank = msg.data + 1
                    self.prev = sender
                    self.scene.addlink(sender, self.id, "parent")
                    
                    # If the receiving node is not the root note, send DIO message and DAO message.
                
                    self.scene.nodecolor(self.id, 0.7, 0, 0)
                    self.scene.nodewidth(self.id, 2)
                    yield self.timeout(delay())
                    self.send_DIO()  # keep expanding network

                    # DAO message should be sent with retransmission
                    self.sequence_count = self.sequence_count + 1
                    for i in range(1,retransmissions):
                        self.send_DAO()  # send DAO back to root to establish DODAG tree
                        yield self.timeout(delay()+2)
                        if self.ack[self.sender]:
                            self.ack[self.sender] = False
                            break

            elif msg.type == RPMType.DAO:  # nodes to root
                self.send_ack(sender)
                if msg.sequence not in self.sequences: # if identical message has not been recieved before
                    self.sequences.append(msg.sequence)
                    if self.id is ROOT:
                        msg.path.append(self.id)
                        path = msg.path[::-1]  # reverse list
                        string = find_by_attr(self.root, str(path[-1]))
                        if string:
                            print("node already in dodag "+str(path[-1]))
                        elif path[-1] is not ROOT:
                            for node in path:
                                string = find_by_attr(self.root, str(node))
                                if not string:
                                    Node(str(node), find_by_attr(self.root, str(prevNode)))  # add latest node to root tree
                                prevNode = node

                        for nodes in path:
                            node = sim.nodes[nodes]
                            node.scene.nodecolor(node.id, 0, 0, 1)


                    else:
                        self.next = self.prev
                        yield self.timeout(delay())
                        self.sequence_count = self.sequence_count + 1
                        for i in range(1,retransmissions+1):
                            #print("node {} retransmission {}".format(self.id, i))
                            self.send_DAO(msg)  # send DAO back to root to establish DODAG tree
                            if self.ack[self.prev]:
                                self.ack[self.prev] = False
                                #print("stop retransmission")
                                break
                            yield self.timeout(delay()+2)
                            if i == retransmissions:
                                cprint("TRANSMISSION FAILLED FROM {} TO {}".format(self.id, self.sender),"FAIL")
                        
            # not yet used
            elif msg.type == RPMType.DIS:
                pass
                
            elif msg.type == RPMType.ACK:
                self.ack[sender] = True
                

            elif msg.type == RPMType.DATA:
                self.send_ack(sender)
                if msg.sequence not in self.sequences:
                    self.sequences.append(msg.sequence)
                    if self.id is not msg.dst:
                        yield self.timeout(delay())
                        self.sequence_count = self.sequence_count + 1
                        for i in range(1,retransmissions+1):
                            #print("node {} retransmission {}".format(self.id, i))
                            self.send_data(msg)  
                            if self.ack[self.prev]:
                                self.ack[self.prev] = False
                                #print("stop retransmission")
                                break
                            yield self.timeout(delay()+2)
                            if i == retransmissions:
                                cprint("TRANSMISSION FAILLED FROM {} TO {}".format(self.id, self.sender),"FAIL")
                            
                    else:
                        printstr = "node " + str(self.id) + " received: " + msg.data
                        cprint(printstr, "OKGREEN")


    # ----------------- Demo functions ----------------

    def root_print_tree(self):
        if self.id is ROOT:
            for pre, fill, node in RenderTree(self.root):  # print tree
                cprint(pre + node.name, "OKCYAN")

        else:
            cprint("Err: Function only available to root node", "WARNING")

    def path_to_node(self, node):
        """
        Takes node number as either str or int
        returns list of path-nodes from root to node.
        """
        if not type(node) == int: node = int(node)
        string = ""
        if self.id is ROOT:
            if node >= 0 or node <= len(sim.nodes) + 1:
                # find by attr gives weird format back, put each item (ie node jump) into list
                string = str(find_by_attr(self.root, str(node)))[7:].split("/")
                string = [int(re.sub("[^0-9]", "", item)) for item in
                          string]  # removes everything but numbers in the list
                # print(string) # print path from root to node
                return string
            else:
                cprint("Err: Node doesnt exist", "WARNING")

        else:
            cprint("Err: Function only available to root node", "WARNING")
        return string


def user_input():
    while (True):
        inp = input(">>")
        try:
            if inp.lower() == "q":
                exit(0)
            elif inp.isnumeric():
                sim.nodes[ROOT].path_to_node(inp)
                rplMsg = RPLMessage(type=RPMType.DATA, src=ROOT, dst=int(inp), data="hello from root :)")
                sim.nodes[ROOT].send_data(rplMsg)
            elif inp[0].lower() == "n":
                rplMsg = RPLMessage(type=RPMType.DATA, src=inp[1:], dst=ROOT,
                                    data="hello from node {} :)".format(inp[1:]))
                sim.nodes[int(inp[1:])].send_data(rplMsg)
            elif inp.lower() == "tree":
                sim.nodes[ROOT].root_print_tree()
        except:
            cprint("Error with input", "WARNING")


###########################################################

tsize = 800
sim = wsp.Simulator(
    until=1000,
    timescale=1,
    visual=True,
    terrain_size=(tsize, tsize),
    title="IPv6 RPL")

# define a line style for parent links
sim.scene.linestyle("parent", color=(0, .8, 0), arrow="tail", width=2)

#
th = threading.Thread(target=user_input)
th.start()
# place nodes over 100x100 grids

for x in range(grid):
    for y in range(grid):
        px = 50 + x * (tsize / 10) * (10 / grid) + random.uniform(-20, 20)
        py = 50 + y * (tsize / 10) * (10 / grid) + random.uniform(-20, 20)
        node = sim.add_node(MyNode, (px, py))

        node.tx_range = (tsize / 9) * (10 / grid) * 1.2

        node.logging = True

# start the simulation
sim.run()
