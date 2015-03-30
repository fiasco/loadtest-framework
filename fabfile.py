import os

from fabric.api import *
from fabric.utils import puts
from fabric import colors
from fabric.contrib import files
import fabric.network
import fabric.state
import fabric.operations
import digitalocean
import re
import pprint
import time




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
    config_filename = 'config.yaml'

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
    config_filename = 'config.yaml'

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
  if 'servers' in config:
    env.group = {}
    for key in config['servers']:
      server = config['servers'][key]
      env.group[server['host']] = server
    env.hosts = env.group.keys()
  else:
    print colors.yellow("No hosts found to load.")

def cluster():
  """Setup the cluster for parallel commands"""
  _load_hosts()
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

@parallel
def debug():
  config = _load_config()
  # pprint.pprint(config)
  try:
    droplet = digitalocean.Droplet(token=config['token'], id=env.id)
    droplet.load()
    actions = droplet.get_actions()
    for action in actions:
      if action.type == 'create' and action.status == 'completed':
        print colors.green("%s %s %s" % (droplet.name, action.type, action.status))
  except Exception:
    print colors.red("Failed to load server.")
    pass

def _setup_host():
  _load_hosts()
  env.user = 'jmeter'
  env.key_filename = 'files/jmeter-id_rsa'
  env.disable_known_hosts = True

@parallel
def setup():
    """Setup remote host to run jmeter as a master or slave environment"""
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
      run('apt-get update; apt-get install unzip openjdk-7-jre-headless snmpd iftop -y')
      run('id jmeter > /dev/null 2&>1 || adduser jmeter --disabled-password --system --shell /bin/bash')
      run('test -f /home/jmeter/apache-jmeter-' + jmeter_version + '.tgz || wget -P /home/jmeter http://www.webhostingjams.com/mirror/apache//jmeter/binaries/apache-jmeter-' + jmeter_version + '.tgz')
      run('tar -C /home/jmeter/ -xf /home/jmeter/apache-jmeter-' + jmeter_version + '.tgz;')
      run('test -d /home/jmeter/apache-jmeter || mv /home/jmeter/apache-jmeter-' + jmeter_version + ' /home/jmeter/apache-jmeter')
      run('test -f home/jmeter/JMeterPlugins-Standard-1.1.3.zip || wget -P /home/jmeter http://jmeter-plugins.org/downloads/file/JMeterPlugins-Standard-1.1.3.zip')
      run('unzip -o /home/jmeter/JMeterPlugins-Standard-1.1.3.zip -d /home/jmeter/apache-jmeter/')
      # run('test -f /home/jmeter/groovy-binary-2.4.0-beta-3.zip || wget -P /home/jmeter http://dl.bintray.com/groovy/maven/groovy-binary-2.4.0-beta-3.zip')
      # run('unzip -o /home/jmeter/groovy-binary-2.4.0-beta-3.zip -d /home/jmeter/')
      # run('cp /home/jmeter/groovy-2.4.0-beta-3/lib/* /home/jmeter/apache-jmeter/lib/ext/')

      run('mkdir -p /var/log/jmeter; chown jmeter /var/log/jmeter')

      put('files/jmeter-server', '/home/jmeter/apache-jmeter/bin/jmeter-server')
      put('files/jmeter', '/home/jmeter/apache-jmeter/bin/jmeter')

    run('mkdir -p /home/jmeter/.ssh/')
    put('files/jmeter-id_rsa.pub', '/home/jmeter/.ssh/authorized_keys')
    run('chown jmeter -R /home/jmeter')
    run('chmod 700 /home/jmeter/.ssh')

def csshx():
  _setup_host()
  cmd = '\tcsshX --ssh_args="-o User=jmeter -o IdentityFile=%s/files/jmeter-id_rsa  -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no" ' % os.path.dirname(env.real_fabfile)
  for h in env.hosts:
    cmd += ' ' + str(h)
  print colors.green("Use this command to open up cluster SSH terminals to the cluster: https://github.com/brockgr/csshx")
  print cmd

@parallel
def upload(asset):
  """Upload jmeter asset to remote host"""
  _setup_host()
  put(asset, '/home/jmeter')

@parallel
def download_logs():
  """Download Jmeter logs from the last load test"""
  _setup_host()
  local('mkdir %s' % env.host)
  run('gzip -9 /var/log/jmeter/*.jtl')
  get('/var/log/jmeter/*.gz', '%s/' % env.host)
  run('rm /var/log/jmeter/*.gz')

def create(namespace="lr", cluster_size=1, hosting_region='nyc2', server_size='1gb'):
  """Create serverson DigitalOcean to become jmeter servers"""
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

    # # Reload the droplet which should now have an id and IP
    # droplet.load()
    config['servers'][droplet.name] = {
      'host': str(droplet.ip_address),
      'id': int(droplet.id)
    }

  _write_config(config=config)

def destroy():
  config = _load_config()
  if  not config['token']:
    print colors.red("DigitalOcean API Token is missing from config.")
    return

  manager = digitalocean.Manager(token=config['token'])

  for key in config['servers']:
    server = config['servers'][key]
    try:
      droplet = manager.get_droplet(server['id'])
      droplet.load()
      droplet.destroy()
      print colors.green('%s will be destroyed.' % key)
      config['servers'].pop(key, None)
    except Exception:
      print colors.red('Could not destory %s.' % key)

  _write_config(config=config)
      
def _server_name(t, i, r):
  prefix = 'j'
  return prefix + str(r) + t + str(i)
