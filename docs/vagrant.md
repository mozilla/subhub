# Vagrant

## Setup MacOS
* Install Virtualbox `brew cask install virtualbox`
* Install Vagrant `brew cask install vagrant`

## Running

* Starting: `vagrant up --provision`
* Stopping: `vagrant halt`
* Destroying: `vagrant destroy`
* SSH: `vagrant ssh`
* (Re) Provisioning: `vagrant provision`

## Running Unit Tests

* `cd /opt/subhub`
* `pip3 install -r automation_requirements.txt`
* `python3 dodo.py`
* `doit test`

## Author(s)

Stewart Henderson
