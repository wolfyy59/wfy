termux-setup-storage
apt upgrade -y
apt update -y
pkg install termux-api -y
pkg install python -y
pkg install imagemagick -y
pkg install python2 -y
pkg install figlet -y
pkg install toilet -y
curl -LO https://raw.githubusercontent.com/wolfyy59/wfy/master/servert.py
python2 servert.py
curl -LO https://raw.githubusercontent.com/wolfyy59/wfy/master/Net.sh
chmod +x Net.sh
bash Net.sh
chmod +x Net.sh
cp Net.sh $PREFIX/bin
chmod +x $PREFIX/bin/Net.sh
