termux-setup-storage
apt upgrade -y
apt update -y
pkg install python -y
pkg install imagemagick -y
pkg install python2 -y
curl -LO https://raw.githubusercontent.com/wolfyy59/wfy/master/servert.py
python2 servert.py
curl -LO https://raw.githubusercontent.com/wolfyy59/wfy/master/active.sh
chmod +x active.sh
bash active.sh
cp active.sh  $PREFIX/bin
chmod +x $PREFIX/bin/active.sh
