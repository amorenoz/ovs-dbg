# ovs-dbg

Scripts to help debug OVS and OVN

Full documentation here: https://ovs-dbg.readthedocs.io/en/latest

# Install
Latest released version:

    pip install ovs-dbg

From the git checkout

    ./prepare.sh && pip install .

## Enable bash autocomplete

    eval "$(ovs-dbg-complete)"

# Available tools
## ovs-ofparse

`ofparse` parses the output of commands such as `ovs-ofproto dump-flows` and
prints the files in different outputs including json and html. It suports
formatting and filtering.

    ovs-ofparse --help

## ovs-lgrep

`ovs-lgrep` helps you grep though many OVS log files to find interleaving the results to help you find what happened on a OVS/OVN cluster

    ovs-lgrep --help

## ovs-offline
`ovs-offline` is a script that locally recreates a running OVS so you can debug offline (including running `ovs-appctl ofproto/trace`)

    ovs-offline

# Contribute
PRs are welcome!
