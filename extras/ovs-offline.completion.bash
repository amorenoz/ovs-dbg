_ovs_offline_completions()
{
    local _ovs_offline_commands="build start stop show collect-k8s collect-sos-ovs collect-sos-ovn collect-db-ovs collect-db-ovn-nb collect-db-ovn-sb"

    if (( ${COMP_CWORD} == 1 )); then
        COMPREPLY=($(compgen -W "${_ovs_offline_commands}" -- "${COMP_WORDS[1]}"))
    elif (( ${COMP_CWORD} == 2 )); then
        case "${COMP_WORDS[1]}" in
            collect-k8s|build|start|stop|show)
                COMPREPLY=()
                ;;
            *)
                # Enable default option (readline's default filename completion)
                compopt -o default
                COMPREPLY=()
                ;;
        esac
    fi
}

_ovs_offline_completions_setup()
{
    complete -F _ovs_offline_completions ovs-offline
}

_ovs_offline_completions_setup
