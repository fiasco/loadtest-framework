loadtest-framework
==================

Puppet configuration for a deployable jmeter loadtesting cluster

Installation
------------
First off, you'll need to install puppet & git on each VM

```
apt-get install puppet git
```

Then checkout this repository inplace of the puppet repository on the local filesystem

```
rm /etc/puppet
git clone https://github.com/fiasco/loadtest-framework.git puppet
```

Install jmeter and plugins with user account and logging directory

```
puppet apply /etc/puppet/manifests/common.pp
```
