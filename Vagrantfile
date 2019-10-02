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
    config.vm.synced_folder "./", "/opt/subhub", type: "rsync",
                            rsync__auto: true,
                            rsync__exclude: ['node_modules*', 'venv', '.doit.db']

    config.vm.provider "virtualbox" do |vb|
      vb.name = "TravisCI"

      # Disallow Desktop login
      vb.gui = false

      vb.memory = "2048"
      vb.customize ["setextradata", :id, "VBoxInternal2/SharedFoldersEnableSymlinksCreate/v-root", "1"]
    end

    config.vm.provision :shell, path: "./bin/vagrant.sh"
  end
