import os

from fabric.api import *
from fabric.utils import puts
from fabric import colors
from fabric.contrib import files
from fabric.contrib import console
import fabric.network
import fabric.state
import fabric.operations
import digitalocean
import re
import pprint
import time
import copy




YAML_AVAILABLE = True
try:
    import yaml
except ImportError:
    YAML_AVAILABLE = False

################################
#         ENVIRONMENTS         #
################################

def _load_config(**kwargs):
    """Find and parse server config file.

    If `config` keyword argument wasn't set look for default
    'server_config.yaml' or 'server_config.json' file.

    """
    config_filename = '%s/config.yaml' % os.path.dirname(env.real_fabfile)

    if not os.path.exists(config_filename):
        print colors.red('Error. "%s" file not found.' % (config_filename))
        return {}
    if YAML_AVAILABLE:
        loader = yaml
    else:
        print colors.red('Parser package not available')
        return {}
    # Open file and deserialize settings.
    with open(config_filename) as config_file:
        return loader.load(config_file)

def _write_config(config):
    config_filename = '%s/config.yaml' % os.path.dirname(env.real_fabfile)

    if YAML_AVAILABLE:
        loader = yaml
    else:
        print colors.red('Parser package not available')
        return {}
    # Open file and deserialize settings.
    with open(config_filename, "w") as config_file:
      config_file.write(loader.dump(config, default_flow_style=False))

def _load_hosts():
  config = _load_config()
  if 'servers' in config and config['servers']:
    env.group = {}
    for key in config['servers']:
      server = config['servers'][key]
      env.group[server['host']] = server
    env.hosts = env.group.keys()
    return config['servers']
  else:
    print colors.yellow("No hosts found to load.")
    return []

@task(alias='go')
def cluster():
  """Setup the cluster for parallel commands, in general you should always run this task before any other"""
    
  print colors.cyan('Running cluster: %s' % ', '.join(_load_hosts().keys()))
  env.parallel = True

def hosts():
    """List the servers and IPs available to the cluster."""
    # Load config
    config = _load_config()
    # If no arguments were recieved, print a message with a list of available configs.
    if 'servers' in config:
        for key in config['servers']:
            print colors.green('%s\t%s' % (key, config['servers'][key]['host']))
    else:
      print colors.red('No hosts available. Try create some first.')


def _setup(task):
    """
    Copies server config settings from `env.group` dictionary to env variable.

    This way, tasks have easier access to server-specific variables:
        `env.owner` instead of `env.group[env.host]['owner']`

    """
    _load_config()
    def task_with_setup(*args, **kwargs):
        # If `s:server` was run before the current command - then we should copy values to
        # `env`. Otherwise, hosts were passed through command line with `fab -H host1,host2
        # command` and we skip.
        if env.get("group", None):
            for key,val in env.group[env.host].items():
                setattr(env, key, val)
                if fabric.state.output['debug']:
                    puts("[env] %s : %s" % (key, val))

        task(*args, **kwargs)
        # Don't keep host connections open, disconnect from each host after each task.
        # Function will be available in fabric 1.0 release.
        # fabric.network.disconnect_all()
    return task_with_setup

#############################
#          TASKS            #
#############################

@_setup

def _setup_host():
  _load_hosts()
  env.user = 'jmeter'
  env.key_filename = '%s/files/jmeter-id_rsa' % os.path.dirname(env.real_fabfile)
  env.disable_known_hosts = True
  env.forward_agent = True

@parallel
@task(alias='setUp')
def setup():
    """Setup remote host to run JMeter as a master or slave environment"""
    # Setup requires root privleges
    env.user = "root"
    env.disable_known_hosts = True
    jmeter_version="2.13"

    config = _load_config()

    try:
      print colors.green("Checking the status of the server")
      for key in config['servers']:
        if config['servers'][key]['host'] == env.host:
          droplet = digitalocean.Droplet(token=config['token'], id=config['servers'][key]['id'])
          droplet.load()
          actions = droplet.get_actions()
          for action in actions:
            if action.type == 'create' and action.status != 'completed':
              raise Exception('Cannot continue, server is not active', 'setup')
          print colors.green("Server is active")
    except Exception as e:
      pprint.pprint(e)
      print colors.red("Failed to load server: %s" % e)
      return

    if not files.exists('/home/jmeter/apache-jmeter/bin/jmeter-server'):
      run('apt-get update > /dev/null; apt-get install git-all unzip openjdk-7-jre-headless snmpd iftop -y > /dev/null')
      run('id jmeter > /dev/null 2&>1 || adduser jmeter --disabled-password --system --shell /bin/bash')
      run('test -f /home/jmeter/apache-jmeter-' + jmeter_version + '.tgz || wget -P /home/jmeter http://apache.mirrors.ionfish.org//jmeter/binaries/apache-jmeter-' + jmeter_version + '.tgz')
      run('tar -C /home/jmeter/ -xf /home/jmeter/apache-jmeter-' + jmeter_version + '.tgz;')
      run('test -d /home/jmeter/apache-jmeter || mv /home/jmeter/apache-jmeter-' + jmeter_version + ' /home/jmeter/apache-jmeter')
      run('test -f home/jmeter/JMeterPlugins-Standard-1.1.3.zip || wget -P /home/jmeter http://jmeter-plugins.org/downloads/file/JMeterPlugins-Standard-1.1.3.zip')
      run('test -f home/jmeter/JMeterPlugins-Extras-1.2.1.zip || wget -P /home/jmeter http://jmeter-plugins.org/downloads/file/JMeterPlugins-Extras-1.2.1.zip')
      run('unzip -o /home/jmeter/JMeterPlugins-Standard-1.1.3.zip -d /home/jmeter/apache-jmeter/')
      run('unzip -o /home/jmeter/JMeterPlugins-Extras-1.2.1.zip -d /home/jmeter/apache-jmeter/')

      run('mkdir -p /var/log/jmeter; chown jmeter /var/log/jmeter')

      put('%s/files/jmeter' % os.path.dirname(env.real_fabfile), '/home/jmeter/apache-jmeter/bin/jmeter')
      run('ln -s /home/jmeter/apache-jmeter/bin/jmeter /usr/local/bin/jmeter')

    run('mkdir -p /home/jmeter/.ssh/')
    put('%s/files/jmeter-id_rsa.pub' % os.path.dirname(env.real_fabfile), '/home/jmeter/.ssh/authorized_keys')
    run('chown jmeter -R /home/jmeter')
    run('chmod 700 /home/jmeter/.ssh')

    if not files.exists('/home/jmeter/.ssh/config'):
      run('echo -e "StrictHostKeyChecking no\n" > /home/jmeter/.ssh/config')

@task
def csshx():
  """Outputs a command you can run to cluster SSH into all servers"""
  _setup_host()
  cmd = '\tcsshX --ssh_args="-o User=jmeter -o IdentityFile=%s/files/jmeter-id_rsa  -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no" ' % os.path.dirname(env.real_fabfile)
  for h in env.hosts:
    cmd += ' ' + str(h)
  print colors.green("Use this command to open up cluster SSH terminals to the cluster: https://github.com/brockgr/csshx")
  print cmd

@task
def ssh():
  """List SSH commands to access servers"""
  print colors.green("SSH commands to access servers in the cluster:")
  for h in env.hosts:
    print 'ssh -o User=jmeter -o IdentityFile=%s/files/jmeter-id_rsa  -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no %s' % str(h)

@parallel
@task(alias='gitClone')
def git_clone(repo, branch='master', project='testplan'):
  """(repo,branch,project) Clones a repository using git, defaults to the master branch, and testplan folder"""
  _setup_host()
  run('git clone -b %s %s %s' % (branch, repo, project))

@parallel
@task(alias='gitPull')
def git_pull(project='testplan'):
  """(project) Pulls in latest updates into a git repository, defaults to the testplan folder"""
  _setup_host()
  run('cd %s && git pull' % project)

@parallel
@task(alias='gitCheckout')
def git_checkout(ref='master', project='testplan'):
  """(ref,project) Checks out a branch in a git repository, defaults to the master branch and testplan folder"""
  _setup_host()
  run('cd %s && git checkout -b %s' % (project, ref))

@parallel
@task
def upload(asset):
  """(asset) Upload JMeter asset to remote host"""
  _setup_host()
  put(asset, '/home/jmeter')

@parallel
@task(alias="downloadLogs")
def download_logs(log_dir="/var/log/jmeter"):
  """(log_dir) Download JMeter logs from the last load test"""
  _setup_host()
  local('mkdir %s' % env.host)
  run('gzip -9 %s/*.jtl' % log_dir)
  get('%s/*.gz', '%s/' % (log_dir, env.host))
  run('rm %s/*.gz' % log_dir)

@task(alias="spinUp")
def create(namespace="lr", cluster_size=1, hosting_region='nyc2', server_size='1gb'):
  """(namespace,cluster_size,hosting_region,server_size) Create servers on DigitalOcean to become JMeter servers"""

  if not console.confirm(colors.blue("You're about to spin up %dx %s servers in %s region. Are you sure?" % (cluster_size, server_size, hosting_region))): 
    abort("Aborting at user request")

  n = int(cluster_size)

  config = _load_config()

  if 'servers' not in config:
    config['servers'] = {}

  if  not config['token']:
    print colors.red("DigitalOcean API Token is missing from config.")
    return

  manager = digitalocean.Manager(token=config['token'])
  droplets = []

  for i in range(1, n + 1):
    server_name = _server_name(namespace, i, hosting_region)

    droplet = digitalocean.Droplet(token=config['token'],
                               name=server_name,
                               region=hosting_region, # New York 2
                               image='ubuntu-14-04-x64', # Ubuntu 14.04 x64
                               size_slug=server_size,  # 512MB
                               ssh_keys=[config['ssh_key']],
                               backups=False)
    print colors.green("Creating %s...." % server_name)
    droplet.create()
    droplets.append(droplet)

  for droplet in droplets:
    droplet.load()

    while not droplet.ip_address:
      print colors.yellow("Waiting for %s to be assigned IP address" % droplet.name)
      time.sleep(5)
      droplet.load()

    print colors.green("%s assigned %s" % (droplet.name, droplet.ip_address))

    # # Reload the droplet which should now have an id and IP
    # droplet.load()
    config['servers'][droplet.name] = {
      'host': str(droplet.ip_address),
      'id': int(droplet.id)
    }

  _write_config(config=config)

@task(alias='tearDown')
def destroy():
  """Tear down and remove all servers in the cluster"""

  if not console.confirm(colors.red("You're about to ALL the servers in the cluster. Are you sure?")): 
    abort("Aborting at user request")

  config = _load_config()
  if  not config['token']:
    print colors.red("DigitalOcean API Token is missing from config.")
    return

  manager = digitalocean.Manager(token=config['token'])

  servers = copy.copy(config['servers'])

  for key in servers:
    server = config['servers'][key]
    try:
      droplet = manager.get_droplet(server['id'])
      droplet.load()
      droplet.destroy()
      print colors.green('%s will be destroyed.' % key)
    except Exception:
      print colors.red('Could not destory %s.' % key)
    config['servers'].pop(key, None)

  _write_config(config=config)

@task(alias='setDNS')
def set_dns(hostname, ip):
  """(hostname, ip) Add a host entry to the /etc/hosts file"""
  env.user = 'root'
  env.disable_known_hosts = True
  env.forward_agent = True
  run('echo "%s %s" >> /etc/hosts' % (ip, hostname))

def _server_name(t, i, r):
  prefix = 'j'
  return prefix + str(r) + t + str(i)
