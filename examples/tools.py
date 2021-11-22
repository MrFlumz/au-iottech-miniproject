



from enum import Enum

colors = {
    "HEADER" : "\033[95m",
    "OKBLUE" : "\033[94m",
    "OKCYAN" : "\033[96m",
    "OKGREEN" : "\033[92m",
    "WARNING" : "\033[93m",
    "FAIL" : "\033[91m",
    "ENDC" : "\033[0m",
    "BOLD" : "\033[1m",
    "UNDERLINE" : "\033[4m"
}

def foo():
    foo.counter = 90

foo.counter = 90
def cprint(string, atribute):
    """
    "HEADER", "OKBLUE", "OKCYAN", "OKGREEN" 
    "WARNING", "FAIL", "ENDC", "BOLD", "UNDERLINE"
    """
    
    if False:
        for element in string:
            if foo.counter > 96:
                foo.counter = 90
            else:
                foo.counter = foo.counter + 1
            col = foo.counter
            print("\033["+str(col)+"m"+element, end='')
        print(str(colors["ENDC"])+"\n")
    print(colors[atribute]+str(string)+str(colors["ENDC"]))