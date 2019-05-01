import logging
import os
import signal
import subprocess

import psutil


here_dir = os.path.abspath(os.path.dirname(__file__))
root_dir = os.path.dirname(os.path.dirname(here_dir))
ddb_dir = os.path.join(root_dir, "ddb")

ddb_process = None
pynamodb_resource = None


def setUp():
    print(f'test setup')
    for name in ('boto3', 'botocore'):
        logging.getLogger(name).setLevel(logging.CRITICAL)
    global ddb_process, pynamodb_resource

    cmd = " ".join(["dynalite --port 8000"])
    ddb_process = subprocess.Popen(cmd, shell=True, env=os.environ)


def tearDown():
    global ddb_process
    # This kinda sucks, but its the only way to nuke the child procs
    proc = psutil.Process(pid=ddb_process.pid)
    child_procs = proc.children(recursive=True)
    for p in [proc] + child_procs:
        os.kill(p.pid, signal.SIGTERM)
    ddb_process.wait()
