mkdir -p /opt/myapp
chmod 755 /opt/myapp
apt install -y nginx curl
touch /tmp/file.txt
cp /tmp/file.txt /var/log/
mv /tmp/file.txt /var/tmp/
md5sum /etc/passwd
wget http://example.com/file.txt
wget http://example.com/index.html -O /tmp/index.html
systemctl start nginx
systemctl enable nginx
echo "Hello world" > /etc/motd
