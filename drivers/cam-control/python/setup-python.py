import os
if "PYTHONPATH" in os.environ:
    del os.environ["PYTHONPATH"]
import subprocess
import sys
import glob
import argparse
import re

### Check Python interpreter
if os.path.abspath(sys.executable)!=os.path.abspath("./python.exe"):
    print("This script should be run in the folder with python.exe used to execute it")
    sys.exit(1)

### Setup comman line arguments
parser=argparse.ArgumentParser()
parser.add_argument("--quiet","-q",action="store_true",help="do not print any script output, except for errors (pip output is still printed)")
parser.add_argument("--force",action="store_true",help="force execution in the already set up environment")
parser.add_argument("--requirements","-r",action="append",help="specify requirements file to install after the basic setup")
parser.add_argument("--test",action="store_true",help="install testing packages: pytest and tox")
parser.add_argument("--dev",action="store_true",help="install developing tools: all packages required for pylablib and jupyter")
parser.add_argument("--pylablib",action="store_true",help="install pylablib")
clargs=parser.parse_args()

def print_verbose(*args, **kwargs):
    if not clargs.quiet:
        print(*args,**kwargs)

### Check if the environment was already set up
pth_files=glob.glob("./python*._pth")
if not pth_files:
    print("Could not find ._pth file",file=sys.stderr)
    sys.exit(1)
if (not clargs.force) and all([os.path.exists(f+".bak") for f in pth_files]):
    print_verbose("The environment is already set up; use --force to force the re-execution")
    exit(0)

### Modify python._pth files
def modify_pth(path):
    os.rename(path,path+".bak")
    adjusted=False
    with open(path+".bak","r") as src, open(path,"w") as dst:
        for ln in src.readlines():
            m=re.match(r"^\s*#\s*(import\s+site\s*)$",ln)
            if m:
                dst.write(m[1])
                adjusted=True
            else:
                dst.write(ln)
    if not adjusted:
        print("Could not adjust ._pth file: expected line is missing",file=sys.stderr)
        sys.exit(1)
for f in pth_files:
    if os.path.exists(f+".bak"):
        print_verbose("Skipping adjusting {}".format(f))
    else:
        modify_pth(f)

### Install and upgrade pip
subprocess.call([r".\python.exe","get-pip.py"])
subprocess.call([r".\python.exe","-m","pip","install","-U","pip","setuptools"])

### Install additional packages
if clargs.requirements:
    subprocess.call([r".\python.exe","-m","pip","install","-r"]+clargs.requirements)
packages=[]
if clargs.test or clargs.dev:
    packages+=["pytest","tox"]
if clargs.dev:
    packages+=["jupyter","ipython"]
    if not clargs.pylablib:
        packages+=["numpy","scipy","matplotlib","numba","pandas","pyqt5","sip","pyqtgraph","pyvisa","pyft232","pyserial","rpyc"]
    packages+=["websocket-client","nidaqmx","pillow","imageio"]
if clargs.pylablib:
    packages+=["pylablib"]
if packages:
    subprocess.call([r".\python.exe","-m","pip","install","-U"]+packages)