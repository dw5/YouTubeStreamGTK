#
# Regular cron jobs for the stream-0.1.0 package
#
0 4	* * *	root	[ -x /usr/bin/stream-0.1.0_maintenance ] && /usr/bin/stream-0.1.0_maintenance
