#!/bin/env sh
set -eu
python -m pip install flake8
git submodule init && git submodule update --recursive
[ -d ovs_dbg/vendor ] || mkdir ovs_dbg/vendor
cd ovs
ls -lha
[ -f configure ] || ./boot.sh
[ -f Makefile ] || ./configure
make python/ovs/dirs.py flake8-check
cd python && pip install -t ../../ovs_dbg/vendor .

