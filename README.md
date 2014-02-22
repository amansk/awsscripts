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
