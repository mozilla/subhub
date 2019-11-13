#!/usr/bin/env bash

display_usage() {
	echo "This script must be run with super-user privileges."
	echo -e "\nUsage:\n attach-gdb {sub,hub}/app.py \n"
	}

function attach(){
    sudo gdb -p $(pgrep -f $1)
}

if [[ $USER != "root" ]]; then
	echo "This script must be run as root!"
	exit 1
fi

if [  $# -le 0 ]; then
		display_usage
		exit 1
fi
attach $1
