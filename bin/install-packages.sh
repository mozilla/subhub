#!/usr/bin/env bash

# Alpine Registry for package versions, https://pkgs.alpinelinux.org/packages
apk update

ALPINE_VERSION=v3.9
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
IFS=$'\n' read -d '' -r -a lines < "${DIR}/../etc/alpine-packages"
apk add  --no-cache --update-cache --repository "http://nl.alpinelinux.org/alpine/${ALPINE_VERSION}/main" "${lines[@]}"
