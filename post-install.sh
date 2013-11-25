#!/usr/bin/env sh

# This script will install and launch the instance of the panel
# On your system
# You will need root access (or being a sudoer, but change the "su -c" by "sudo")
# Enjoy.
source is_installed.sh

case ${INSTALLED} in
    0) su -c "python3 setup.py install" && sed -i "s/INSTALLED=0/INSTALLED=1/" > is_installed.sh ;;
    1) break ;;
esac

python3 setup.py develop --user &&
python3 tfh.py -c development.ini initdb &&
PATH="~/.local/bin/:$PATH" ; # If it's not done yet
pserve development.ini 
