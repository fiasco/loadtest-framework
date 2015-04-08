# loadtest-framework

Fabric for a deployable jmeter loadtesting cluster on Digital Ocean

## Installation

You'll need [Fabric](http://www.fabfile.org/), a python deployment tool,the Digital Ocean library (python-digitalocean) and the YAML parser for Python.

```
sudo easy_install pip
sudo pip install Fabric python-digitalocean PyYAML pyopenssl ndg-httpsclient pyasn1
```

Its also recommended that you install [csshX](https://github.com/brockgr/csshx) (or cssh if you're not using Mac)

**Tip:** Download and install [Tugboat CLI](https://github.com/pearkes/tugboat) as a quick lookup for the digital ocean API

```
sudo gem install tugboat
```

## Usage

Create a yaml file called <code>config.yaml</code> in this directory. Inside it, you should put your [Digital Ocean Token](https://www.digitalocean.com/community/tutorials/how-to-use-the-digitalocean-api-v2) and SSH key ID

```
ssh_key: 123456
token: 77e027c7447f468068a7d4fea41e7149a75a94088082c66fcf555de3977f69d3
```

Your SSH key ID can be found by using this cURL command with *your* token:
```
curl -X GET -H 'Content-Type: application/json' -H 'Authorization: Bearer 77e027c7447f468068a7d4fea41e7149a75a94088082c66fcf555de3977f69d3' "https://api.digitalocean.com/v2/account/keys"
```
*Note:* This returns in JSON so you'll need to read through the formatting to find the correct ID value.

### Create a JMeter Cluster

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

Once a cluster of servers has been created, a command called "cluster" can be used in fabric to run commands in parallel on the servers.

```
fab cluster setup
```

This command should install all the requirements onto the servers to allow JMeter to run. Here is what it does at a high level:

* Install Java
* Install JMeter
* Create JMeter user
* Create JMeter directories (home, log)
* Setup password-less SSH access

Now you're all setup to run JMeter as a cluster.

### Running a Test

Once you've created a test, you'll want to upload it to all the servers and run it. You can either manually upload the JMeter JMX file:

```
fab cluster upload:TestPlan.jmx
```

Or, alternatively you can clone a git repository on the servers (this is useful if your test plan for example uses CSV files):

```
fab cluster git_clone:git@github.com:wiifm69/loadtest-files.git
```

The above commands will upload the test plan file <code>TestPlan.jmx</code> to the servers in parallel.

```
fab csshx
```

This will output a csshX command that you can run to deploy a cluster of shells that can be commanded by a single red terminal. We'll use this to execute the load test.

On the JMeter servers:

```
jmeter -n -t ~/TestPlan.jmx
```

This will kick off the test and run each JMeter server independently.

### Download the logs and clean up

After the test is complete and you want to get access to the results

```
fab cluster download_logs
```

An finally to destroy the servers

```
fab cluster destroy
```

The log files will now be locally stored, and you can concatenate them together:

```
find . |  grep gz | xargs cat > all.gz && gunzip all.gz && mv all jmeter-logs.jtl
```

Then you can open the jmeter-logs.jtl file in JMeter, the transactions per second graph is very interesting to view:

![transactions per second graph example](images/transactions-per-second.png)
