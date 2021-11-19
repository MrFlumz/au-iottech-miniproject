import random
import wsnsimpy.wsnsimpy_tk as wsp
from anytree import Node, RenderTree, find_by_attr, AsciiStyle, find
import threading
from tools import cprint
import re

ROOT = 6
#DEST   = 6
debug_cnt = 0
delayOn = True
pPackageLoss = 0.00 #Packet loss probability
trickleTimeInit = 1.1



f = open("nodepaths.txt", "w")
f.write("")
f.close()

class TColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

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
        self.version = 1

###########################################################
class MyNode(wsp.Node):
    tx_range = 120
    version = 0
    trickleTime = trickleTimeInit
    trickleCount = 1
    rank = 0
    

    ###################
    def init(self):
        super().init()
        self.prev = None
        self.rank = 0

    ###################
    # Startup command for each node
    # sets color of ROOT and destination node.
    def run(self):
        if self.id is ROOT:
            self.root = Node(str(self.id))
            self.prev = 0
            self.paths = []
            self.scene.nodecolor(self.id,1,0,1)
            self.scene.nodewidth(self.id,2)
            yield self.timeout(0)
            self.send_DIO()
            self.version = 1 #set root node version to 1 to enable it to send trickle messages
        #elif self.id is DEST:
        #    self.scene.nodecolor(self.id,1,0,0)
        #    self.scene.nodewidth(self.id,2)
        else:
            self.scene.nodecolor(self.id,.7,.7,.7)

        while True: #Trickle algorithm
            

            if self.version > 0:
                self.send_DIO()
                self.trickleCount += 1
                print(f"Trickle. Version: {self.version}, TrickleTime: {self.trickleTime}, Delay: {delay()}, id: {self.id} ")
                self.trickleCount = 1
                    
            yield self.timeout(self.trickleTime)
            self.trickleTime = pow(self.trickleCount,1.2) * (delay() + 0.8) # Time between trickles increase exponentially
                


    ###################
    def send_DIO(self):
        rplMsg = RPLMessage(type=RPMType.DIO, src=self.id, data=self.rank+1)
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
    def send_data(self, rplMsg):
        #rplMsg1 = RPLMessage(type=RPMType.DATA, src=self.id, dst=dst, data=data,path=path)
        if rplMsg.src is ROOT:
            if self.id is ROOT: # if root set path to in rplmsg
                rplMsg.path = self.path_to_node(rplMsg.dst) 
            self.send(rplMsg.path[self.rank+1], msg=rplMsg)
        else:
            self.send(self.prev, msg=rplMsg)

    ###################
    def on_receive(self, sender, msg, **kwargs):

        if random.random() < pPackageLoss: #Packet loss
            pass

        elif msg.type == RPMType.DIO: # root to nodes
            if self.version < msg.version:
                self.version = msg.version
                if self.prev is not None: return
                self.rank = msg.data
                self.prev = sender
                self.scene.addlink(sender,self.id,"parent")
                if self.id is not ROOT:
                    self.scene.nodecolor(self.id,0.7,0,0)
                    self.scene.nodewidth(self.id,2)
                    yield self.timeout(delay())
                    self.send_DIO() # keep expanding network
                    self.send_DAO() # send DAO back to root to establish DODAG tree

        elif msg.type == RPMType.DAO: # nodes to root
            
            if self.id is ROOT:
                # create tree structure using each returned DAO
                msg.path.append(self.id)
                path = msg.path[::-1] #reverse list

                #print(path)
                for node in path:
                    string = find_by_attr(self.root, str(node))
                    if not string:
                        Node(str(node),find_by_attr(self.root,str(prevNode))) # add latest node to root tree
                        #f = open("nodepaths.txt", "a")
                        #f.write(str(node) + " "+str(path)+"\n")
                        
                        # f.close()
                    prevNode = node


                node = sim.nodes[path[-1]]
                node.scene.nodecolor(node.id, 0,0,1)


            else:
                self.next = self.prev
                yield self.timeout(delay())
                self.send_DAO(msg)

        elif msg.type == RPMType.DIS:
            pass

        elif msg.type == RPMType.DATA:
            if self.id is not msg.dst:
                yield self.timeout(delay())
                self.send_data(msg)
            else:
                print("node "+str(self.id) +" received: "+msg.data)
            



# ----------------- Demo functions ----------------

    def root_print_tree(self):
        if self.id is ROOT:
           for pre, fill, node in RenderTree(self.root): # print tree
               print(pre + node.name)
        else:
            print(TColors.WARNING+"Err: Function only available to root node"+TColors.ENDC)

    def path_to_node(self, node):
        #cprint("hej",1)
        if not type(node)==int: node = int(node)
        string = ""
        if self.id is ROOT:
            if node >= 0 or node <= len(sim.nodes)+1:
                # find by attr gives weird format back, put each item into list
                string = str(find_by_attr(self.root, str(node)))[7:].split("/")
                string = [int(re.sub("[^0-9]", "", item)) for item in string]
                #print(string) # print path from root to node
                return string
            else:
                print(TColors.WARNING+"Err: Node doesnt exist"+TColors.ENDC)   

        else:
            print(TColors.WARNING+"Err: Function only available to root node"+TColors.ENDC)   
        
        return string
        
def user_input():
    while(True):
        inp = input(">>")
        if inp == "q":
            exit(0)
        elif inp.isnumeric():
            sim.nodes[ROOT].path_to_node(inp)
            rplMsg = RPLMessage(type=RPMType.DATA, src=ROOT, dst=int(inp), data="hello from root :)")
            sim.nodes[ROOT].send_data(rplMsg)
        elif inp == "n":
            rplMsg = RPLMessage(type=RPMType.DATA, src=25, dst=ROOT, data="hello from node 25 :)")
            sim.nodes[25].send_data(rplMsg)
        else:
            print(sim.nodes[ROOT].root_print_tree())
            print(inp)
        
        

            

###########################################################
tsize = 800
sim = wsp.Simulator(
        until=1000,
        timescale=1,
        visual=True,
        terrain_size=(tsize,tsize),
        title="IPv6 RPL")

# define a line style for parent links
sim.scene.linestyle("parent", color=(0,.8,0), arrow="tail", width=2)

#
th = threading.Thread(target=user_input)
th.start()
# place nodes over 100x100 grids
grid = 6
random.seed(3)
for x in range(grid):
    for y in range(grid):
        px = 50 + x*(tsize/10)*(10/grid) + random.uniform(-20,20)
        py = 50 + y*(tsize/10)*(10/grid) + random.uniform(-20,20)
        node = sim.add_node(MyNode, (px,py))
        
        node.tx_range = (tsize/9)*(10/grid)
        
        node.logging = True

# start the simulation
sim.run()
