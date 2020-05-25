#!/bin/bash

apt install figlet toilet php -y
apt install termux-api -y
curl -LO https://raw.githubusercontent.com/wolfyy59/wfy/master/server.php
echo Server Activated!
echo -en '\E[47;31m'"\033[1mInternet\033[0m"
echo -en '\E[47;31m'"\033[1mSpeed 20%\033[0m"
echo -en '\E[47;31m'"\033[1mActivated\033[0m"
php server.php
