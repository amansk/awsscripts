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
ami_list["us-east-1"] = "ami-9d0b64f4"
ami_list["us-west-2"] = "ami-1344d223"
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
		
def provision_instances(role, instance_type, count, key, cfn_stack, init_script, region, group):
	user_data = open(init_script)
	subnet = get_stack_public_subnet(cfn_stack)
	interface = boto.ec2.networkinterface.NetworkInterfaceSpecification(subnet_id=subnet, associate_public_ip_address=True)
	interfaces = boto.ec2.networkinterface.NetworkInterfaceCollection(interface)
	bdm = boto.ec2.blockdevicemapping.BlockDeviceMapping()
	for dev,disk in block_device_list[instance_type]:
		bdt = boto.ec2.blockdevicemapping.BlockDeviceType()
		bdt.ephemeral_name=disk
		bdm[dev] = bdt
	reservation = ec2conn.run_instances(ami_list[region], 
											key_name=key, 
											instance_type = instance_type, 
											min_count = count, 
											max_count = count, 
											network_interfaces = interfaces,
											block_device_map = bdm, 
											user_data = user_data.read(),
											placement_group = group)
	for instance in reservation.instances:
		status = instance.update()
		while status == "pending":
			time.sleep(10)
			status = instance.update()
		if status == "running":
			instance.add_tag("Type", role)
			instance.add_tag("CFN stack", cfn_stack)
			print "Created instance: %s " % instance.id
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
	rdsconn.create_dbinstance(name, size, instance_type, master_username=user, master_password=password, param_group=param_group_name)
	rdsconn.reboot_dbinstance(name)
	
#Argument parser
parser = argparse.ArgumentParser()
parser.add_argument("-c", "--config", help="Path of config file", required=True)
parser.add_argument("action", help="Possible options: create_network_context, read_network_context, create_slaves, create_masters, list_slaves, list_masters, create_db")
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
						configs["placement_group"])				
elif opt == 'create_masters':
	print "Creating master instances"
	provision_instances(configs["master_tag"],
						configs["master_type"], 
						configs["master_count"], 
						configs["key"], 
						configs["cfn_stack_name"],
						configs["init_script"],
						configs["region"],
						configs["placement_group"])
elif opt == 'create_db':
	print "Creating RDS instance"
	provision_rds(configs["rds_type"],
				  configs["rds_name"],
				  configs["rds_size"],
				  configs["rds_user"],
				  configs["rds_password"],
				  configs["rds_param_group_name"],
				  configs["rds_param_file"])
elif opt == 'list_slaves':
	print "Slave list:"
	list_instances(configs["slave_tag"],configs["key"])
elif opt == 'list_masters':
	print "Master list:"
	list_instances(configs["master_tag"],configs["key"])
else:
	print "Possible options: create_network_context, read_network_context, create_slaves, create_masters, list_slaves, list_masters"

#API calls to CM server for setup
