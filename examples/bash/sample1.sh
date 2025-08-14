
MYDIR=/opt/mydir
MY_DIR_EXTRA=/opt/mydir/extra
umask 0077
mkdir -p $MYDIR
umask 0057
mkdir -p $MY_DIR_EXTRA
ln -s /usr/bin/python $MYDIR/python-link
ln /usr/bin/python $MYDIR/python-soft-link
ldconfig
gunzip /tmp/archive.gz
apt update
apt install -y foo floob
apt install bar
apt update
apt-get update
if [ $? -eq 0 ]; then
   echo "Either mycommand failed or <foo failed"
fi
if [  "$foo" -eq "wibble" ]; then
   echo "they are the same"
   apt install doobydo
fi

if [ $? -eq 0 ]; then
   apt install flimble
fi