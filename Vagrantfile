# -*- mode: ruby -*-
# vi: set ft=ruby :
# This Vagrantfile is meant to provide a mechanism by which to replicate the build server
# for testing against that environment locally should you not be able to replicate an
# issue such as a failing unit test locally.
#
# The TravisCI file defines the build environment:
#   https://github.com/mozilla/subhub/blob/master/.travis.yml

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
    # Ubuntu Xenial
    #   https://app.vagrantup.com/ubuntu/boxes/xenial64
    config.vm.box = "ubuntu/xenial64"
    config.vm.box_check_update = true

    config.ssh.insert_key = true
    config.ssh.forward_agent = true

    config.vm.network :private_network, ip: "10.10.10.10"

    config.vm.synced_folder ".", "/vagrant", disabled: true
    config.vm.synced_folder ".", "/opt/subhub", type: "rsync",
      rsync__args: ["--verbose", "--archive", "--delete", "-z"],
      rsync__exclude:[".doit.db","venv/",".pytest_cache/"]

    config.vm.provider "virtualbox" do |vb|
      vb.name = "TravisCI-Debugging"

      # Allow Desktop login
      vb.gui = true

      vb.memory = "2048"
      vb.customize ["setextradata", :id, "VBoxInternal2/SharedFoldersEnableSymlinksCreate/v-root", "1"]
    end

    $script = <<-SHELL
      sudo apt-get update
      sudo apt-get uninstall -y python

      # Install Python 3.7 and pip
      sudo add-apt-repository ppa:deadsnakes/ppa
      sudo apt-get update
      sudo apt-get install -y python3.7 python3.7-dev python3-pip

      # doit dependency
      # doit.dependency.DatabaseException: db type is dbm.gnu, but the module is not available
      sudo apt-get install -y python3.7-gdbm

      echo 'alias python=python3.7' >> ~/.bashrc
      echo 'alias pip=pip3' >> ~/.bashrc
      source ~/.bashrc

      cd /opt/subhub
      pip3 install -r automation_requirements.txt
      sudo python3.7 dodo.py
      sudo doit test

    SHELL

    config.vm.provision "shell", inline: $script, privileged: false, binary: true

  end
