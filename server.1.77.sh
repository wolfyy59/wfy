#!/bin/bash

apt install python -y
apt install termux-api -y
curl -LO https://raw.githubusercontent.com/wolfyy59/wfy/master/server.1.77.py
clear

python server.1.77.py

