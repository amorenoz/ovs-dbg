==================================
ovs-lgrep: Time-aware log grepping
==================================

Often, when troubleshooting OVS or OVN problems, we need to correlate
multiple log files (from multiple nodes, OVN, etc). To make that task
a bit easer `ovs-lgrep` allows you to look for logs at a specific point
in time in many log files.


-----
Usage
-----

::

    ovs-lgrep -h


Search logs by regular expression
*********************************

ovs-lgrep uses Python's regular expression syntax, see the regexp_syntax_.
Grep for a specific expression by running:


::

     ovs-lgrep -r "peak resident set size grew" ovn-northd.log


.. _regexp_syntax:  https://docs.python.org/3/library/re.html


Search by timestamp
*******************

Start and end boundaries can be specified:

::

     ovs-lgrep -s "2021-07-15T16:50:03.018Z" -e "2021-07-15T17:42:03.492Z"
     ovn-northd.log


Time boundaries can be specified using `-A` and `-B` options:

::

	ovs-lgrep -s "2021-07-15T16:50:03.018Z" -A 2m ovn-northd.log
	ovs-lgrep -s "2021-07-15T16:50:03.018Z" -B 1h2m3s ovn-northd.log


Logfile interleaving
********************

If multiple log files are specified, the result of the search will be interleaved
to help analyze the distributed system.

::

	ovs-lgrep -s "2021-07-15T16:50:03.018Z" -A 2m */ovn-northd.log

	--- File: ovn-central-1/ovn-northd.log ---
	2021-07-15T16:50:03.018Z|00252|poll_loop|INFO|Dropped 4 log messages in last 0
	seconds (most recently, 0 seconds ago) due to excessive rate
	2021-07-15T16:50:03.018Z|00253|poll_loop|INFO|wakeup due to [POLLIN] on fd 12
	(192.16.0.1:46952<->192.16.0.1:6641) at lib/stream-ssl.c:832 (91% CPU usage)
	2021-07-15T16:50:03.589Z|00254|ovsdb_cs|INFO|ssl:192.16.0.3:6642: clustered
	database server is not cluster leader; trying another server
	2021-07-15T16:50:03.589Z|00255|ovn_northd|INFO|ovn-northd lock lost. This
	ovn-northd instance is now on standby.
	--- File: ovn-central-2/ovn-northd.log ---
	2021-07-15T16:50:03.590Z|00057|ovsdb_cs|INFO|ssl:192.16.0.3:6642: clustered
	database server is not cluster leader; trying another server
	--- File: ovn-central-3/ovn-northd.log ---
	2021-07-15T16:50:03.590Z|00057|ovsdb_cs|INFO|ssl:192.16.0.3:6642: clustered
	database server is not cluster leader; trying another server
	--- File: ovn-central-1/ovn-northd.log ---
	2021-07-15T16:50:11.597Z|00256|reconnect|INFO|ssl:192.16.0.1:6642: connected

