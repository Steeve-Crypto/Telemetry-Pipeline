#!/bin/sh
python3 -c "
import urllib.request
urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3)
"