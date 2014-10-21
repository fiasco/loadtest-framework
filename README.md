loadtest-framework
==================

Fabric configuration for a deployable jmeter loadtesting cluster

Installation
------------

You'll need [Fabric](http://www.fabfile.org/), a python deployment tool. This can be done through the Python package manager, pip.

```
pip install fabric
```


Usage
-----
Before you use this tool, you need to have your servers available. You should have:
* 1 master jmeter server
* 1 or more slave jmeter servers
* The ability to login to the servers as root
* All servers are connected via a local network (private networking or other)

### Setup the jmeter servers
Checkout this repository

```
git clone git@github.com:fiasco/loadtest-framework.git 
```

(Optional) Setup ssh keys to override the ones in this repository as they are insecure since they are openly available.

```
cd loadtest-framework
ssh key-gen -f files/jmeter-id_rsa
```

Run setup to install all the tech needed on the servers and the ssh access keys for jmeter.

```
fab -H <jmeter_master>,<jmeter_slave_1>,... setup
```

### Initialise the Jmeter Slaves
Kick off the jmeter slaves in screen sessions

```
fab -H <jmeter_slave_1>,... run_slaves
```

### Run the load test on the Jmeter master
This is going to be better implemented with fabric but for now, obtain ssh command for the jmeter server:

```
fab -H <jmeter_master> ssh
ssh -i files/jmeter-id_rsa jmeter@<jmeter_master>
screen
./apache-jmeter/bin/jmeter -t <loadtest>.jmx -n -R <jmeter_slave_1_internal_ip>,....
```


