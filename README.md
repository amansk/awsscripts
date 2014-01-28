Scripts for Cloudera deployments in AWS
==========

This github consists of the following artifacts:

1. Cloudformation templates for network context setup (VPC, subnet etc)
2. Python scripts for instance provisioning

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
