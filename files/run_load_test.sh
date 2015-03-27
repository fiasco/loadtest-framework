#!/bin/bash

# Rotate logs if present.
if [ -f /var/log/jmeter/ideaden-loadtest.log ]; then
	echo "Rotating logs.."
	logrotate --force /root/jmeter_logrotate 
fi

echo "Running Load Test..."

RMI_HOST_DEF=-Djava.rmi.server.hostname=`ifconfig | grep eth1 -A 1 | grep inet | cut -d ':' -f 2 | awk '{print $1}'`

/root/apache-jmeter-2.11/bin/jmeter ${RMI_HOST_DEF} -n -r -t /root/LaunchReady.jmx
