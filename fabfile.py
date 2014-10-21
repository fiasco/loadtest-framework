from fabric.api import *
import os

def setup():
    jmeter_version="2.11"
    print("Installing unzip openjdk-7-jre-headless snmpd -y")
    run('apt-get update; apt-get install unzip openjdk-7-jre-headless snmpd iftop -y')
    print("Installing jmeter user")
    run('id jmeter > /dev/null 2&>1 || adduser jmeter --disabled-password --system --shell /bin/bash')
    print("Downloading jmeter binary")
    run('test -f /home/jmeter/apache-jmeter-' + jmeter_version + '.tgz || wget -P /home/jmeter http://apache.claz.org/jmeter/binaries/apache-jmeter-' + jmeter_version + '.tgz')
    print("Extracting jmeter")
    run('tar -C /home/jmeter/ -xf /home/jmeter/apache-jmeter-' + jmeter_version + '.tgz;')
    print("Installing jmeter")
    run('test -d /home/jmeter/apache-jmeter || mv /home/jmeter/apache-jmeter-' + jmeter_version + ' /home/jmeter/apache-jmeter')
    print("Downloading jmeter plugins")
    run('test -f home/jmeter/JMeterPlugins-Standard-1.1.3.zip || wget -P /home/jmeter http://jmeter-plugins.org/downloads/file/JMeterPlugins-Standard-1.1.3.zip')
    print("Unziping jmeter plugins")
    run('unzip -o /home/jmeter/JMeterPlugins-Standard-1.1.3.zip -d /home/jmeter/apache-jmeter/')
    print('Setting up logging directory')
    run('mkdir -p /var/log/jmeter; chown jmeter /var/log/jmeter')

    print('Installing jmeter executables')
    put('files/jmeter-server', '/home/jmeter/apache-jmeter/bin/jmeter-server')
    put('files/jmeter', '/home/jmeter/apache-jmeter/bin/jmeter')

    print('Installing jmeter keys')
    run('mkdir -p /home/jmeter/.ssh/')
    put('files/jmeter-id_rsa.pub', '/home/jmeter/.ssh/authorized_keys')
    run('chown jmeter -R /home/jmeter')
    run('chmod 700 /home/jmeter/.ssh')

def screen_kill():
  env.user = 'jmeter'
  env.key_filename = 'files/jmeter-id_rsa'
  run('screen -X -S jmeter-session quit')

def run_slaves():
  env.user = 'jmeter'
  env.key_filename = 'files/jmeter-id_rsa'
  with cd('/home/jmeter/apache-jmeter/bin'):
    run('screen -dmS jmeter-session ./jmeter-server -n', pty=False)

def upload_jmx(jmx):
  env.user = 'jmeter'
  env.key_filename = 'files/jmeter-id_rsa'
  put(jmx, '/home/jmeter')

def run_master(jmx, slaves):
  env.user = 'jmeter'
  env.key_filename = 'files/jmeter-id_rsa'
  put(jmx, '/home/jmeter')
  run('screen -dmS ./apache-jmeter/bin/jmeter -t "' + os.path.basename(jmx) + '" -n -R ' + slaves.replace(';', ','), pty=False) 

def check():
  env.user = 'jmeter'
  env.key_filename = 'files/jmeter-id_rsa'
  with settings(warn_only=True):
    run('screen -ls')

def master_check_connectivity(slaves):
  for slave in slaves.split(';'):
    run('ping -c 1 ' + slave)

def ssh():
  env.user = 'jmeter'
  env.key_filename = 'files/jmeter-id_rsa'
  print "ssh -i " + env.key_filename + " " + env.user + "@" + env.host
