loadtest-framework
==================

Fabric for a deployable jmeter loadtesting cluster on Digital Ocean

Installation
------------

You'll need [Fabric](http://www.fabfile.org/), a python deployment tool,the Digital Ocean library (python-digitalocean) and the YAML parser for Python.

```
pip install Fabric python-digitalocean PyYAML
```

Its also recommended that you install csshX (or cssh if you're not using Mac): https://github.com/brockgr/csshx

Usage
-----
Create a yaml file called config.yaml in this directory. Inside it, you should put your [Digital Ocean Token](https://www.digitalocean.com/community/tutorials/how-to-use-the-digitalocean-api-v2) and SSH Key ID

```
ssh_key: 123456
token: 77e027c7447f468068a7d4fea41e7149a75a94088082c66fcf555de3977f69d3
```

*Tip:* Download and install Tugboat CLI as a quick lookup for the digital ocean API: https://github.com/pearkes/tugboat

### Create a Jmeter Cluster
Creating a cluster is done in two easy steps:
```
fab create:cluster_size=2
```
This will create a two server cluster. There are also other options:
* namespace: used to namespace the names of the servers. Defaults to lr.
* cluster_size: the number of servers to create in the region. Defaults to 1.
* hosting_region: the region to deploy the servers to. Defaults to nyc2.
* server_size: The size of the servers to deploy. Defaults to 1gb.

The create command will write the created servers to the config.yaml file. You can run the command multiple times to deploy multiple servers into different regions or namespaces.

Once a cluster of servers has been created, a command called "cluster" can be used in fabirc to run commands in parallel on the servers.

```
fab cluster setup
```

This command should install all the requirements onto the servers to allow jmeter to run. Here is what it does at a high level:
* Install Java
* Install Jmeter
* Create Jmeter user
* Create Jmeter directories (home, log)
* Setup passwordless SSH access

Now you're all setup to run jmeter as a cluster.

### Running a Test
Once you've created a test, you'll want to upload it to all the servers and run it.
```
fab cluster upload:TestPlan.jmx
```
The above command will upload the Test Plan file, TestPlan.jmx to the servers in parallel.

```
fab csshx
```
This will output a csshx command that you can run to deploy a cluster of shells that can be commanded by a single red terminal. We'll use this to execute the load test.

On the jmeter servers:
```
./apache-jmeter/bin/jmeter -n -t TestPlan.jmx
```

This will kick off the test and run each jmeter server independantly.
