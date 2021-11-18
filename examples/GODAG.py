import random
import wsnsimpy.wsnsimpy_tk as wsp
from anytree import Node, RenderTree, find_by_attr, AsciiStyle, find

ROOT = 6
#DEST   = 6
debug_cnt = 0
delayOn = True

from enum import Enum
class RPMType(Enum):
    DIO = 1
    DAO = 2
    DIS = 3
    DATA = 4


###########################################################
def delay():
    if delayOn:
        return random.uniform(.2,.8)
    else:
        return 0

class RPLMessage:
    def __init__(self, type = 1, src="", dst="", data="", path=[]) -> None:
        self.type = RPMType(type)
        self.src = src
        self.dst = dst
        self.data = data
        self.path = path

###########################################################
class MyNode(wsp.Node):
    tx_range = 100
    

    ###################
    def init(self):
        super().init()
        self.prev = None

    ###################
    # Startup command for each node
    # sets color of ROOT and destination node.
    def run(self):
        if self.id is ROOT:
            self.root = Node(str(self.id))
            self.paths = []
            self.scene.nodecolor(self.id,0,0,1)
            self.scene.nodewidth(self.id,2)
            yield self.timeout(0)
            self.send_DIO()
        #elif self.id is DEST:
        #    self.scene.nodecolor(self.id,1,0,0)
        #    self.scene.nodewidth(self.id,2)
        else:
            self.scene.nodecolor(self.id,.7,.7,.7)

    ###################
    def send_DIO(self):
        rplMsg = RPLMessage(type=RPMType.DIO, src=self.id)
        self.send(wsp.BROADCAST_ADDR, msg=rplMsg)

    ###################
    def send_DAO(self,rplMsg = None):
        if rplMsg is None:
            list = [self.id]
            rplMsg = RPLMessage(type=RPMType.DAO, src=self.id,path=list)
        else:
            rplMsg.path.append(self.id)

        #if self.id is not DEST:
        #    self.scene.nodecolor(self.id,0,.7,0)
        #    self.scene.nodewidth(self.id,2)
        self.send(self.prev, msg=rplMsg)

    ###################
    def start_send_data(self):
        #self.scene.clearlinks()
        seq = 0
        while True:
            yield self.timeout(1)
            self.log(f"Send data to {DEST} with seq {seq}")
            self.send_data(seq)
            seq += 1

    ###################
    def send_data(self,seq):
        self.log(f"Forward data with seq {seq} via {self.next}")
        rplMsg = RPLMessage(type=RPMType.DATA, src=self.id,data=seq)
        self.send(self.next, msg=rplMsg)

    ###################
    def on_receive(self, sender, msg, **kwargs):
        
        if msg.type == RPMType.DIO: # root to nodes
            if self.prev is not None: return
            self.prev = sender
            self.scene.addlink(sender,self.id,"parent")
            if self.id is not ROOT:
                self.scene.nodecolor(self.id,0.7,0,0)
                self.scene.nodewidth(self.id,2)
            # if self.id is DEST:
            #     self.log(f"Receive DIO from {msg.src}")
            #     yield self.timeout(0)
            #     self.log(f"Send DAO to {msg.src}")
            #     self.send_DAO()
            #else:
            #    yield self.timeout(delay())
            #    self.send_DIO()
                yield self.timeout(delay())
                self.send_DIO() # keep expanding network
                self.send_DAO() # send DAO back to root to establish DODAG tree

        elif msg.type == RPMType.DAO: # nodes to root
            
            if self.id is ROOT:

                # create tree structure using each returned DAO
                msg.path.append(self.id)
                path = msg.path[::-1] #reverse list
                #print(path)
                Node(str(path[-1]),find_by_attr(self.root,str(path[-2]))) # add latest node to root tree
                
                global debug_cnt # only print when all nodes are discovered
                debug_cnt = debug_cnt + 1
                if debug_cnt + 1 == len(sim.scene.nodes):
                    #print(RenderTree(self.root))
                    for pre, fill, node in RenderTree(self.root): # print tree
                        print(pre + node.name)
                    print(str(find_by_attr(self.root, "35"))[7:].replace("/"," -> ")) # print path from root to node 24
                        
            else:
                self.next = self.prev
                yield self.timeout(delay())
                self.send_DAO(msg)

        elif msg.type == RPMType.DIS:
            pass

        elif msg.type == RPMType.DATA:
            if self.id is not DEST:
                yield self.timeout(delay())
                self.send_data(msg.data)
            else:
                seq = msg.data
                self.log(f"Got data from {msg.src} with seq {seq}")

 
            

###########################################################
sim = wsp.Simulator(
        until=100,
        timescale=1,
        visual=True,
        terrain_size=(700,700),
        title="AODV Demo")

# define a line style for parent links
sim.scene.linestyle("parent", color=(0,.8,0), arrow="tail", width=2)

# place nodes over 100x100 grids
grid = 6
for x in range(grid):
    for y in range(grid):
        px = 50 + x*70*(10/grid) + random.uniform(-20,20)
        py = 50 + y*70*(10/grid) + random.uniform(-20,20)
        node = sim.add_node(MyNode, (px,py))
        
        node.tx_range = 80*(10/grid)
        
        node.logging = True

# start the simulation
sim.run()
