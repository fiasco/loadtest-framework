package { 'unzip':
  ensure => installed,
}

group { "jmeter":
  ensure => present,
  gid => 5001,
}

user { "jmeter":
  ensure => present,
  uid => '5001',
  gid => 'jmeter',
  shell => '/bin/sh',
  home => '/home/jmeter',
  managehome => true,
}

file { '/var/log/jmeter':
  ensure => directory,
  owner => 'jmeter',
  group => 'jmeter',
  mode => '640',
}

exec { "download_jmeter":
  unless => 'test -f /home/jmeter/apache-jmeter-2.11.tgz',
  path => ['/usr/bin','/usr/sbin','/bin','/sbin'],
  user => 'jmeter',
  command => '/usr/bin/wget -P /home/jmeter http://apache.claz.org//jmeter/binaries/apache-jmeter-2.11.tgz',
}

exec { "extract_jmeter":
  unless => 'test -d /home/jmeter/apache-jmeter',
  path => ['/usr/bin','/usr/sbin','/bin','/sbin'],
  user => 'jmeter',
  command => 'tar -C /home/jmeter/ -xf /home/jmeter/apache-jmeter-2.11.tgz; mv /home/jmeter/apache-jmeter-2.11 /home/jmeter/apache-jmeter',
  require => Exec['download_jmeter'],
}

exec { "download_jmeter_plugins":
  unless => 'test -f /home/jmeter/JMeterPlugins-Standard-1.1.3.zip',
  path => ['/usr/bin','/usr/sbin','/bin','/sbin'],
  command => '/usr/bin/wget -P /home/jmeter http://jmeter-plugins.org/downloads/file/JMeterPlugins-Standard-1.1.3.zip',
  user => 'jmeter',
}

exec { "extract_jmeter_plugins":
  command => 'unzip -o /home/jmeter/JMeterPlugins-Standard-1.1.3.zip -d /home/jmeter/apache-jmeter/',
  path => ['/usr/bin','/usr/sbin','/bin','/sbin'],
  user => 'jmeter',
  unless => 'test -f /home/jmeter/apache-jmeter/lib/ext/JMeterPlugins-Standard.jar',
  require => Exec['download_jmeter_plugins'],
}

file { "/tmp/jmeter":
  source => 'puppet://files/jmeter',
  owner => 'jmeter',
  group => 'jmeter',
  mode => 640,
}

file { "/tmp/jmeter-server":
  source => 'puppet://files/jmeter-server',
  owner => 'jmeter',
  group => 'jmeter',
  mode => 640,
}

exec { "replace_jmeter_binary":
  require => [Exec['extract_jmeter'], File['/tmp/jmeter']],
  command => 'mv /tmp/jmeter /home/jmeter/apache-jmeter/bin/jmeter',
  path => ['/usr/bin','/usr/sbin','/bin','/sbin'],
  user => 'jmeter',
}
  
exec { "replace_jmeter_server_binary":
  require => [Exec['extract_jmeter'], File['/tmp/jmeter-server']],
  command => 'mv /tmp/jmeter-server /home/jmeter/apache-jmeter/bin/jmeter-server',
  path => ['/usr/bin','/usr/sbin','/bin','/sbin'],
  user => 'jmeter',
}
