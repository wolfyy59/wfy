#!/bin/bash
clear
echo 'Installing Requirements....'
echo .
echo .
apt install figlet toilet php -y
echo This Script Was Made By wolfyy2009 >update.speedx
echo Requirements Installed....
echo Press Enter To Continue...
read upd
fi
while :
do
rm *.xxx >/dev/null 2>&1
clear
echo -e "\e[1;31m"
figlet Portforward
echo -e "\e[1;34m Created By \e[1;32m"
toilet -f mono12 -F border Wolfyy
echo -e "\e[4;34m This forwarder Was Created By wolfyy  \e[0m"
echo -e "\e[1;34m For Any Queries Mail Me!!!\e[0m"
echo -e "\e[1;32m           Mail: wolfyyt@gmail.com \e[0m"
echo -e "\e[4;32m   YouTube Page: https://www.youtube.com/wolfyy2009 \e[0m"
echo " "
echo -e "\e[4;31m Please Read Instruction Carefully !!! \e[0m"
echo " "
echo "Press 1 To  Start SMS Bomber "
echo "Press 2 To  Start Call Bomber "
echo "Press 3 To  Update (Works On Linux And Linux Emulators) "
echo "Press 4 To  View Features "
echo "Press 5 To  Exit "
read ch
if [ $ch -eq 1 ];then
clear
echo -e "\e[1;32m"
rm *.xxx >/dev/null 2>&1
php hak.php
rm *.xxx >/dev/null 2>&1
exit 0
done
