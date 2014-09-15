apt-get -y install puppet git
rm -rf /etc/puppet
git clone https://github.com/fiasco/loadtest-framework.git /etc/puppet
puppet apply /etc/puppet/manifests/common.pp
