#!/usr/bin/env bash
###############################################################################
#
#   circle-ci-configuration.sh
#
###############################################################################

# From the sh(1) man page of FreeBSD:
# Exit immediately if any untested command fails. in non-interactive
# mode.  The exit status of a command is considered to be explicitly
# tested if the command is part of the list used to control an if,
# elif, while, or until; if the command is the left hand operand of
# an “&&” or “||” operator; or if the command is a pipeline preceded
# by the ! operator.  If a shell function is executed and its exit
# status is explicitly tested, all commands of the function are con‐
# sidered to be tested as well.
set -e

# Return status is that of the last command to fail in a
# piped command, or a zero if they all succeed.
set -o pipefail

EXIT=0

curl -sSL https://deb.nodesource.com/gpgkey/nodesource.gpg.key | sudo apt-key add -
echo "deb https://deb.nodesource.com/node_6.x xenial main" | sudo tee /etc/apt/sources.list.d/nodesource.list
echo "deb-src https://deb.nodesource.com/node_6.x xenial main" | sudo tee -a /etc/apt/sources.list.d/nodesource.list

sudo apt-get update
cat requirements/system/ubuntu/apt-packages.txt | DEBIAN_FRONTEND=noninteractive xargs apt-get -yq install
service mongodb restart

mkdir -p downloads

DEBIAN_FRONTEND=noninteractive apt-get -yq install xvfb libasound2 libstartup-notification0 gettext

export FIREFOX_FILE="downloads/firefox_45.0.2%2Bbuild1-0ubuntu1_amd64.deb"
if [ -f $FIREFOX_FILE ]; then
   echo "File $FIREFOX_FILE found."
else
   echo "Downloading firefox_59.0.1%2Bbuild1-0ubuntu0.16.04.1_amd64.deb."
   curl --silent --show-error --location --fail --retry 3 --output $FIREFOX_FILE https://s3.amazonaws.com/vagrant.testeng.edx.org/firefox_59.0.1%2Bbuild1-0ubuntu0.16.04.1_amd64.deb
fi
dpkg -i $FIREFOX_FILE || DEBIAN_FRONTEND=noninteractive apt-get -fyq install
firefox --version

# libsqlite 3.11.0-1ubuntu1 included with Xenial can cause segfault.
export SQLITE_FILE="downloads/libsqlite3-0_3.19.3-3_amd64.deb"
if [ -f $SQLITE_FILE ]; then
   echo "File $SQLITE_FILE found."
else
   echo "Downloading libsqlite3-0_3.19.3-3_amd64.deb."
   curl --silent --show-error --location --fail --retry 3 --output $SQLITE_FILE http://mirrors.kernel.org/ubuntu/pool/main/s/sqlite3/libsqlite3-0_3.19.3-3_amd64.deb
fi
dpkg -i $SQLITE_FILE || DEBIAN_FRONTEND=noninteractive apt-get -fyq install

