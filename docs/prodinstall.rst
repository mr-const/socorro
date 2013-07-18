.. index:: prodinstall

.. _prodinstall-chapter:

Production Install
======================================

Requirements
````````````

This guide assumes that you have already followed all steps in :ref:`installation-chapter`

Ubuntu
````````````
Install dependencies
::
  sudo apt-get install supervisor rsyslog libapache2-mod-wsgi memcached

Set up directories and permissions
::
  sudo mkdir /etc/socorro
  sudo mkdir /var/log/socorro
  sudo mkdir -p /data/socorro
  sudo useradd socorro
  sudo chown socorro:socorro /var/log/socorro
  sudo mkdir -p /home/socorro/primaryCrashStore /home/socorro/fallback /home/socorro/persistent
  sudo chown www-data:socorro /home/socorro/primaryCrashStore /home/socorro/fallback
  sudo chmod 2775 /home/socorro/primaryCrashStore /home/socorro/fallback


RHEL/Centos
````````````
Install dependencies
::
  sudo yum install httpd mod_wsgi memcached openldap-devel daemonize mod_ssl rabbitmq-server

Initialize and enable apache at startup
::
  sudo chkconfig httpd on
  sudo chkconfig memcached on
  sudo chkconfig rabbitmq-server on


Set up directories and permissions
::
  sudo mkdir /etc/socorro
  sudo mkdir /var/log/socorro
  sudo mkdir -p /data/socorro
  sudo useradd socorro
  sudo chown socorro:socorro /var/log/socorro
  sudo mkdir /home/socorro/primaryCrashStore /home/socorro/fallback /home/socorro/persistent
  sudo chown apache /home/socorro/primaryCrashStore /home/socorro/fallback
  sudo chmod 2775 /home/socorro/primaryCrashStore /home/socorro/fallback


Install socorro
````````````
From inside the Socorro checkout
::
  make install

By default, this installs files to /data/socorro. You can change this by 
specifying the PREFIX:
::
  make install PREFIX=/usr/local/socorro

Install configuration to system directory
````````````
From inside the Socorro checkout, as the *root* user
::
  cp config/*.ini /etc/socorro/

It is highly recommended that you customize the files
to change default passwords, and include the common_*.ini files
rather than specifying the default password in each config file.

Install Socorro cron job manager
````````````
Socorro's cron jobs are managed by :ref:`crontabber-chapter`.

:ref:`crontabber-chapter` runs every 5 minutes from the system crontab.

copy rc file
::
  cp scripts/crons/socorrorc /etc/socorro/

edit /etc/cron.d/socorro 
::
  */5 * * * * socorro /data/socorro/application/scripts/crons/crontabber.sh


Start daemons
````````````
Add init script
::
  sudo ln -s /data/socorro/application/scripts/init.d/socorro-processor /etc/init.d/
  sudo chkconfig --add socorro-processor
  
To enable rabbitmq processing change line in ``/data/socorro/application/scripts/init.d/socorro-processor`` from
``config=/etc/socorro/processor.ini`` to ``config=/etc/socorro/rabbitmq-processor.ini``

Configure Apache
````````````
Socorro uses three virtual hosts:

* crash-stats   - the web UI for viewing crash reports
* socorro-api   - the "middleware" used by the web UI 
* crash-reports - receives reports from crashing clients (via HTTP POST)

edit collector.wsgi so it will read rabbitmq-collector.ini
::
  if os.path.isfile('/etc/socorro/rabbitmq-collector.ini'):
      config_path = '/etc/socorro/rabbitmq-collector.ini'

Comment out everything in web_server section of the rabbitmq-collector.ini file and append this
::
  wsgi_server_class='socorro.webapi.servers.ApacheModWSGI'
  

As *root*:
::
  cp puppet/files/etc_apache2_sites-available/{crash-reports,crash-stats,socorro-api} /etc/httpd/conf.d/

edit /etc/httpd/conf.d/{crash-reports,crash-stats,socorro-api} and customize
as needed for your site

As *root*
::
  mkdir /var/log/httpd/{crash-stats,crash-reports,socorro-api}.example.com
  chown apache /data/socorro/htdocs/application/logs/

Note - use www-data instead of apache for debian/ubuntu

Activate apache modules
````````````

As *root*
::
  a2enmod headers
  a2enmod proxy
  a2enmod rewrite
