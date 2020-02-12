#!/bin/bash

apt install figlet toilet php -y
echo PfwD and net +20 % speed ACTIVATED!
echo -en '\E[47;31m'"\033[1mInternet\033[0m"
echo -en '\E[47;31m'"\033[1mSpeed 20%\033[0m"
echo -en '\E[47;31m'"\033[1mActivated\033[0m"
php portlocal.php
