#!/bin/bash

apt install figlet toilet php -y
echo PORTFORWARD ACTIVATED!
echo -en '\E[47;31m'"\033[1mActivated\033[0m"
php portlocal.php

