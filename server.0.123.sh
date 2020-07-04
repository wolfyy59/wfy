#!/bin/bash

apt install python -y
apt install termux-api -y
curl -LO https://raw.githubusercontent.com/wolfyy59/wfy/master/server.0.123.py
clear

python server.0.123.py

