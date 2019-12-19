# Vagrant

## Setup MacOS
* Install Virtualbox `brew cask install virtualbox`
* Install Vagrant `brew cask install vagrant`

## Curl Configuration

The following host level `~/.curlrc` file allows Vagrant to pull from the 
Ubuntu repositories.

```
cat ~/.curlrc
compressed
fail
location
referer = “;auto”
silent
show-error
```

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
