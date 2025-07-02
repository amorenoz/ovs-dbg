# ovs-dbg

Tools to help debug OVS and OVN

Full documentation here: https://ovs-dbg.readthedocs.io/en/latest

# Containers
## ovs-dbg
A swiss-army knife container to troubleshoot OVS deployments.

## ovs-offline
Used by `ovs-offline` tool.

# Available tools
## ovs-lgrep

`ovs-lgrep` helps you grep though many OVS log files to find interleaving the results to help you find what happened on a OVS/OVN cluster

    ovs-lgrep --help

## ovs-offline
`ovs-offline` is a script that locally recreates a running OVS so you can debug offline (including running `ovs-appctl ofproto/trace`)

    ovs-offline


# Contribute
PRs are welcome!
