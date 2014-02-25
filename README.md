Scripts for Cloudera deployments in AWS
==========

This github consists of the following artifacts to make provisioning of AWS resources easy for the Cloudera AWS reference architecture:

1. Cloudformation templates for network context setup (VPC, subnet etc)
2. Python scripts for instance provisioning

The Cloudformation templates are used to setup the network context, which consists of the following things:

1. VPC
2. Subnets
3. DNS configuration
4. Gateways
5. Security groups

Once the network context is created, the setup.py script can be used to provision the instances. To have a fully functioning cluster, the following steps need to be performed after the network context is created:

1. Create master and slave instances
2. Prepare the instances (disable SElinux, create partitions, resize root volume etc)
3. Install Cloudera Manager Server on master instance
4. Install Cloudera Manager Agents on slave instances and master instances
5. Deploy Hadoop using CM

The current implementation of the script performs steps 1 and 2. The installation of CM and CDH has to be done manually at this point. Once the steps 1 and 2 are completed, a /tmp/init-complete file is created. After this, you have to restart the instances for some of the configurations to take place. This restart can take some time because the root volume resize takes effect during the restart.

Sample Cloudformation templates are in the cfntemplates folder and the provisioning scripts are in the scripts folder. You have to write a config file as well. A sample config file is available in the scripts folder.

### Setup

To use these scripts, the following setup steps need to be done.

1. Install Boto

		pip install boto

2. Set the following environment variables with your AWS credentials. Put them in your bashrc.

		export AWS_ACCESS_KEY=<my_access_key>
		export AWS_SECRET_KEY=<my_secret_key>

3. Setup the configs for the scripts. These are the in the scripts/config file.

### Example usage

    $ ./setup.py -h
	usage: setup.py [-h] -c CONFIG action

	positional arguments:
	  action                Possible options: create_network_context,
	                        read_network_context, create_slaves, create_masters,
	                        list_slaves, list_masters, create_db

	optional arguments:
	  -h, --help            show this help message and exit
	  -c CONFIG, --config CONFIG
	                        Path of config file

    $ ./setup.py create_network_context

    $ ./setup.py create_slaves
	
	$ ./setup.py create_masters
	
	$ ./setup.py list_slaves
	
	$ ./setup.py list_masters
	
#### Steps to spin up a cluster
1. Set up configs

2. Create network context (VPC, subnets, security groups)

		./setup.py -c <config_file> create_network_context
		
3. Create master instance
		
		./setup.py -c <config_file> create_masters
		
4. Create slave instances and point them to the master instance, where the master instance's IP address is the output of the create_masters command

		./setup.py -c <config_file> -s <master_ip_address> create_slaves

Once the instances are provisioned, the setup script will be executed on them, which will create the mount points, create partitions, install Cloudera Manager server and agents, resize the root volumes and once all steps are done, reboot the instances. When the instances come back up, you'll be able to access the Cloudera Manager UI at http://master\_public\_ip\_address:7180