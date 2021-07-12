OVS_CONTAINERS = ovs-vswitchd ovsdb-server
DOCKER ?= docker

.PHONY:all
all: $(OVS_CONTAINERS)


$(OVS_CONTAINERS):
	cd containers/$@; $(DOCKER) build -t $@ .

