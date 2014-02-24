#! /usr/bin/env python

import boto.cloudformation
import boto.ec2
import boto.rds
import os
import json
import argparse
import time
import sys
import string
import argparse

#Parameters
access_key = os.environ["AWS_ACCESS_KEY"]
secret_key = os.environ["AWS_SECRET_KEY"]
ami_list = {}
ami_list["us-east-1"] = {"hs1.8xlarge":"ami-9d0b64f4", "cc2.8xlarge":"ami-9d0b64f4", "m1.xlarge":"ami-a25415cb"}
ami_list["us-west-2"] = {"hs1.8xlarge":"ami-1344d223", "cc2.8xlarge":"ami-1344d223", "m1.xlarge":"ami-b8a63b88"}
block_device_list = {}
block_device_list["hs1.8xlarge"] = [("/dev/xvdb","ephemeral0"), 
									("/dev/xvdc","ephemeral1"), 
									("/dev/xvdd","ephemeral2"), 
									("/dev/xvde","ephemeral3"), 
									("/dev/xvdf","ephemeral4"), 
									("/dev/xvdg","ephemeral5"), 
									("/dev/xvdh","ephemeral6"), 
									("/dev/xvdi","ephemeral7"), 
									("/dev/xvdj","ephemeral8"), 
									("/dev/xvdk","ephemeral9"), 
									("/dev/xvdl","ephemeral10"), 
									("/dev/xvdm","ephemeral11"), 
									("/dev/xvdn","ephemeral12"), 
									("/dev/xvdo","ephemeral13"), 
									("/dev/xvdp","ephemeral14"), 
									("/dev/xvdq","ephemeral15"), 
									("/dev/xvdr","ephemeral16"), 
									("/dev/xvds","ephemeral17"),
									("/dev/xvdt","ephemeral18"), 
									("/dev/xvdu","ephemeral19"), 
									("/dev/xvdv","ephemeral20"), 
									("/dev/xvdw","ephemeral21"), 
									("/dev/xvdx","ephemeral22"), 
									("/dev/xvdy","ephemeral23")]
block_device_list["cc2.8xlarge"] = [("/dev/xvdb","ephemeral0"), 
									("/dev/xvdc","ephemeral1"), 
									("/dev/xvdd","ephemeral2"), 
									("/dev/xvde","ephemeral3")]
block_device_list["m1.xlarge"] = [("/dev/xvdf","ephemeral0"), 
									("/dev/xvdg","ephemeral1"), 
									("/dev/xvdh","ephemeral2"), 
									("/dev/xvdi","ephemeral3")]
root_device = {"hs1.8xlarge":"/dev/sda1", "cc2.8xlarge":"/dev/sda1", "m1.xlarge":"/dev/sda1"}

class MyBaseException(Exception):
    msg ="MyBaseException"
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return "%s: %s" % (self.msg, self.value)
 
class MissingParamException(MyBaseException):
    msg ="Missing param"
 
class InvalidCommandException(MyBaseException):
    msg ="Invalid command"
 
class InvalidStackException(MyBaseException):
    msg ="Invalid stack"

def get_stack(stack):
	stacks = cfconn.describe_stacks(stack)
	if not stacks:
	    raise InvalidStackException(stack)
	return stacks[0]

def get_stacks():
	return cfconn.list_stacks()
	
def list_cfn_stacks():
	stacks = cfconn.list_stacks()
	for stack in stacks:
		print_stack(get_stack(stack.stack_id))

def create_stack(name, template, key, group):
	cfconn.create_stack(name, template_body = template, parameters = [("KeyPairName",key)])
	ec2conn.create_placement_group(group)
#	ec2conn.authorize_security_group(group_name="default", ip_protocol="tcp", from_port="22", to_port="22", cidr_ip="0.0.0.0/0")

def get_stack_vpc_id(stack):
	outputs = get_stack(stack).outputs
	for f in outputs:
		if f.key == "VPC":
			return f.value

def get_stack_public_subnet(stack):
	outputs = get_stack(stack).outputs
	for f in outputs:
		if f.key == "DMZSubnet":
			return f.value

def get_stack_cluster_sg(stack):
	outputs = get_stack(stack).outputs
	for f in outputs:
		if f.key == "SecurityGroup":
			return f.value

def print_stack(stack):
    print "Name:            %s" % stack.stack_name
    print "ID:              %s" % stack.stack_id
    print "Status:          %s" % stack.stack_status
    print "Creation Time:   %s" % stack.creation_time
    print "Outputs:         %s" % stack.outputs
    print "Parameters:      %s" % stack.parameters
    print "Tags:            %s" % stack.tags
    print "Capabilities:    %s" % stack.capabilities

def get_template_string(path):
	with open(path, 'r') as template:
		return json.dumps(json.load(template))
		
def provision_instances(role, instance_type, count, key, cfn_stack, init_script, region, group, server, license=None):
	user_data = open(init_script)
	subnet = get_stack_public_subnet(cfn_stack)
	security_group = get_stack_cluster_sg(cfn_stack)
	print "Subnet: {}".format(subnet)
	interface = boto.ec2.networkinterface.NetworkInterfaceSpecification(subnet_id=subnet, associate_public_ip_address=True, groups=[security_group])
	interfaces = boto.ec2.networkinterface.NetworkInterfaceCollection(interface)
	bdm = boto.ec2.blockdevicemapping.BlockDeviceMapping()
	for dev,disk in block_device_list[instance_type]:
		bdt = boto.ec2.blockdevicemapping.BlockDeviceType()
		bdt.ephemeral_name=disk
		bdm[dev] = bdt
	root_dev_bdt = boto.ec2.blockdevicemapping.BlockDeviceType()
	root_dev_bdt.size = 100
	bdm[root_device[instance_type]] = root_dev_bdt
	print "Provisioning {} instances and linking to CM server on {}".format(count, server)
	user_data_string = user_data.read()
	if server == "localhost":
		license_file = open(license)
		license_string = license_file.read()
		user_data_string = string.replace(user_data_string, "CMSERVER=false", "CMSERVER=true")
		user_data_string = string.replace(user_data_string, "cm-license", license_string)
	else:
		user_data_string = string.replace(user_data_string, "master-node-ip-address", server)		
	reservation = ec2conn.run_instances(ami_list[region][instance_type], 
											key_name=key, 
											instance_type = instance_type, 
											min_count = count, 
											max_count = count, 
											network_interfaces = interfaces,
											block_device_map = bdm, 
											user_data = user_data_string)
											#placement_group = group)
	for instance in reservation.instances:
		status = instance.update()
		while status == "pending":
			time.sleep(10)
			status = instance.update()
		if status == "running":
			instance.add_tag("Type", role)
			instance.add_tag("CFN stack", cfn_stack)
			instance.add_tag("Name", cfn_stack + "-" + role)
			print "Created instance: {} with public IP: {} ".format(instance.id, instance.ip_address)
		else:
			print "Instance status for %s: %s" % (instance.id , status)
			
def list_instances(role, key):
	filters = {"tag:Type": role, "instance-state-name":"running", "key-name":key}
	reservation = ec2conn.get_all_instances(filters=filters)
	for instance in reservation[0].instances:
		print "ID: %s, Public IP: %s, Private IP: %s" % (instance.id, instance.ip_address, instance.private_ip_address)
		
def provision_rds(instance_type, name, size, user, password, param_group_name, params_file):
	#Setting up RDS parameters
	rds_params_file = open(params_file)
	params = {}
	for line in rds_params_file:
		tokens = string.split(line,"=")
		params[string.strip(tokens[0])] = string.strip(tokens[1])
	rdsconn.create_parameter_group(param_group_name, description = 'Parameter group for Cloudera RDS instance')
	param_group1 = rdsconn.get_all_dbparameters(param_group_name)
	param_group2 = rdsconn.get_all_dbparameters(param_group_name, marker = param_group1.Marker)
	param_group1.get_params()
	param_group2.get_params()
	param_group = dict(param_group1.items() + param_group2.items())
	for param in params.keys():
		rds_param = param_group.get(param)
		rds_param.set_value(params[param])
		rds_param.apply()
	
	#Provisioning RDS instance
	db = rdsconn.create_dbinstance(name, size, instance_type, master_username=user, master_password=password, param_group=param_group_name)
	print "Created DB instance: %s" % db.id
	print "DB instance is currently being set up and the endpoint will be available once it's setup. Use the list_db option to get the endpoint later"

def list_db(name):
	db = rdsconn.get_all_dbinstances(name)[0]
	print "Name: %s ; Host: %s ; Port: %s" % (db.id, str(db.endpoint[0]), db.endpoint[1])
	
#Argument parser
parser = argparse.ArgumentParser()
parser.add_argument("-c", "--config", help="Path of config file", required=True)
parser.add_argument("-s", "--cmserver", help="IP address of CM server")
parser.add_argument("action", help="Possible options: create_network_context, read_network_context, create_slaves, create_masters, list_slaves, list_masters, create_db, list_db")
args = parser.parse_args()
		
#Read config file
configs = {}
config_file = open(args.config)
for line in config_file:
	tokens = string.split(line, "=")
	configs[string.strip(tokens[0])] = string.strip(tokens[1])
			
#Create connections to AWS endpoints
cfconn = boto.cloudformation.connect_to_region(configs["region"], aws_access_key_id = access_key, aws_secret_access_key = secret_key)
ec2conn = boto.ec2.connect_to_region(configs["region"], aws_access_key_id = access_key, aws_secret_access_key = secret_key)
rdsconn = boto.rds.connect_to_region(configs["region"], aws_access_key_id = access_key, aws_secret_access_key = secret_key)

#Starting point of script for all activities
opt = args.action

if opt == 'create_network_context':
	print "Creating network context"
	create_stack(configs["cfn_stack_name"], get_template_string(configs["cfn_template"]), configs["key"], configs["placement_group"])
elif opt == 'read_network_context':
	vpc = get_stack_vpc_id(configs["cfn_stack_name"])
	public_subnet = get_stack_public_subnet(configs["cfn_stack_name"])
	print "VPC ID: %s with public subnet: %s" % (vpc, public_subnet)
elif opt == 'create_slaves':
	print "Creating slave instances"
	provision_instances(configs["slave_tag"], 
						configs["slave_type"], 
						configs["slave_count"], 
						configs["key"], 
						configs["cfn_stack_name"],
						configs["init_script"],
						configs["region"],
						configs["placement_group"],
						args.cmserver)				
elif opt == 'create_masters':
	print "Creating master instances"
	provision_instances(configs["master_tag"],
						configs["master_type"], 
						configs["master_count"], 
						configs["key"], 
						configs["cfn_stack_name"],
						configs["init_script"],
						configs["region"],
						configs["placement_group"],
						"localhost",
						configs["license_file"])
elif opt == 'create_db':
	print "Creating RDS instance"
	provision_rds(configs["rds_type"],
				  configs["rds_name"],
				  configs["rds_size"],
				  configs["rds_user"],
				  configs["rds_password"],
				  configs["rds_param_group_name"],
				  configs["rds_param_file"])
elif opt == 'list_db':
	print"DB instance:"
	list_db(configs['rds_name'])
elif opt == 'list_slaves':
	print "Slave list:"
	list_instances(configs["slave_tag"],configs["key"])
elif opt == 'list_masters':
	print "Master list:"
	list_instances(configs["master_tag"],configs["key"])
else:
	print "Possible options: create_network_context, read_network_context, create_slaves, create_masters, list_slaves, list_masters, create_db, list_db"

#API calls to CM server for setup
