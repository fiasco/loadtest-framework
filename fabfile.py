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

def _write_config(data):
    config_filename = 'config.yaml'
    config = _load_config()
    cluster = []

    for server in data.keys():
        cluster.append(server)

    config.update(data)
    config['cluster'] = cluster

    if YAML_AVAILABLE:
        loader = yaml
    else:
        print colors.red('Parser package not available')
        return {}
    # Open file and deserialize settings.
    with open(config_filename, "w") as config_file:
      config_file.write(loader.dump(config, default_flow_style=False))

def hosts(*args, **kwargs):
    """Set destination servers or server groups by comma delimited list of names"""
    # Load config
    config = _load_config(**kwargs)
    # If no arguments were recieved, print a message with a list of available configs.
    if not args:
        print 'No server name given. Available configs:'
        for key in config['cluster']:
            print colors.green('\t%s' % key)

    # Create `group` - a dictionary, containing copies of configs for selected servers. Server hosts
    # are used as dictionary keys, which allows us to connect current command destination host with
    # the correct config. This is important, because somewhere along the way fabric messes up the
    # hosts order, so simple list index incrementation won't suffice.
    env.group = {}
    # For each given server name
    for name in args:
        #  Recursive function call to retrieve all server records. If `name` is a group(e.g. `all`)
        # - get it's members, iterate through them and create `group`
        # record. Else, get fields from `name` server record.
        # If requested server is not in the settings dictionary output error message and list all
        # available servers.
        _build_group(name, config)


    # Copy server hosts from `env.group` keys - this gives us a complete list of unique hosts to
    # operate on. No host is added twice, so we can safely add overlaping groups. Each added host is
    # guaranteed to have a config record in `env.group`.
    env.hosts = env.group.keys()

def _build_group(name, servers):
    """Recursively walk through servers dictionary and search for all server records."""
    # We're going to reference server a lot, so we'd better store it.
    server = servers.get(name, None)
    # If `name` exists in servers dictionary we
    if server:
        # check whether it's a group by looking for `members`
        if isinstance(server, list):
            if fabric.state.output['debug']:
                    puts("%s is a group, getting members" % name)
            for item in server:
                # and call this function for each of them.
                _build_group(item, servers)
        # When, finally, we dig through to the standalone server records, we retrieve
        # configs and store them in `env.group`
        else:
            if fabric.state.output['debug']:
                    puts("%s is a server, filling up env.group" % name)
            env.group[server['host']] = server
    else:
        print colors.red('Error. "%s" config not found. Run `fab s` to list all available configs' % name)

def _setup(task):
    """
    Copies server config settings from `env.group` dictionary to env variable.

    This way, tasks have easier access to server-specific variables:
        `env.owner` instead of `env.group[env.host]['owner']`

    """
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
  env.user = 'jmeter'
  env.key_filename = 'files/jmeter-id_rsa'
  env.disable_known_hosts = True

def setup():
    """Setup remote host to run jmeter as a master or slave environment"""
    # Setup requires root privleges
    env.user = "root"
    env.disable_known_hosts = True
    jmeter_version="2.13"

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

def start(jmx):
  """Start jmeter"""
  _setup_host()
  put(jmx, '/home/jmeter')
  open_shell('./apache-jmeter/bin/jmeter -t "' + os.path.basename(jmx) + '" -n')

def upload(asset):
  """Upload jmeter asset to remote host"""
  _setup_host()
  put(asset, '/home/jmeter')

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

  if  not config['token']:
    print colors.red("DigitalOcean API Token is missing from config.")
    return

  manager = digitalocean.Manager(token=config['token'])
  droplets = []
  servers = {}

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
    actions = droplet.get_actions()
    for action in actions:
      action.load()
      if (action.type == 'create'):
        while action.status != "completed":
          print colors.yellow("Waiting for %s (%s)" % (droplet.name, action.status))
          time.sleep(5)
          action.load()

        # Once it shows complete, droplet is up and running
        print colors.green("%s %s" % (droplet.name, action.status))

    # Reload the droplet which should now have an id and IP
    droplet.load()
    servers[droplet.name] = {
      'host': str(droplet.ip_address),
      'id': int(droplet.id)
    }

  _write_config(data=servers)

def destroy():
  config = _load_config()
  if  not config['token']:
    print colors.red("DigitalOcean API Token is missing from config.")
    return

  manager = digitalocean.Manager(token=config['token'])
  servers = {}

  for server in config['cluster']:
    servers[server] = config[server]
    try:
      droplet = manager.get_droplet(config[server]['id'])
      droplet.load()
      droplet.destroy()
      print colors.green('%s has been actioned to be destroyed.' % server)
      servers[server] = None
    except Exception:
      print colors.red('Could not destory %s.' % server)

  _write_config(data=servers)
      
def _server_name(t, i, r):
  prefix = 'j'
  return prefix + str(r) + t + str(i)

# csshX --ssh_args="-o User=jmeter -o IdentityFile=~/LaunchReadiness/CoolMath/files/jmeter-id_rsa  -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no"
