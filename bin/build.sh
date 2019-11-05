#!/usr/bin/env bash

# homebrew installation, the preferred method for aws-vault on Linux
sh -c "$(curl -fsSL https://raw.githubusercontent.com/Linuxbrew/install/master/install.sh)"
echo 'eval $(/home/linuxbrew/.linuxbrew/bin/brew shellenv)' >>~/.profile

source ~/.profile

# aws-vault
brew install aws-vault

cd /opt/subhub
pip3 install -r automation_requirements.txt
python3 dodo.py
