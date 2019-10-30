#!/usr/bin/env bash

sudo apt-get update
sudo apt-get uninstall -y python

# Install Python 3.7 and pip
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install -y python3.7 python3.7-dev python3-pip python3.7-venv python3.7-gdb gdb

# Install Yarn
curl -sL https://deb.nodesource.com/setup_10.x | sudo -E bash -
sudo apt-get install -y nodejs

curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | sudo apt-key add -
echo "deb https://dl.yarnpkg.com/debian/ stable main" | sudo tee /etc/apt/sources.list.d/yarn.list
sudo apt-get update
sudo apt-get install -y yarn

# Install AWSCLI
sudo apt-get install -y awscli

# Install docker-compose
sudo curl -L https://github.com/docker/compose/releases/download/1.18.0/docker-compose-`uname -s`-`uname -m` -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# doit dependency
# doit.dependency.DatabaseException: db type is dbm.gnu, but the module is not available
sudo apt-get install -y python3.7-gdbm
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.7 2


echo 'alias python=python3.7' >> ~/.bashrc
echo 'alias pip=pip3' >> ~/.bashrc
echo 'cd /opt/subhub' >> /home/vagrant/.bashrc

source ~/.bashrc
