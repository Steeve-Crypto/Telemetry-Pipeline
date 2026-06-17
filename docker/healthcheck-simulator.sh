#!/bin/sh
python3 -c "
import os, sys, time
path = '/tmp/simulator.heartbeat'
if not os.path.exists(path):
    sys.exit(1)
if time.time() - os.path.getmtime(path) > 120:
    sys.exit(1)
"