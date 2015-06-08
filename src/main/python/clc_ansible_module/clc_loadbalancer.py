#!/usr/bin/python
DOCUMENTATION = '''
module:
short_desciption: Create, Delete shared loadbalancers in CenturyLink Cloud.
description:
  - An Ansible module to Create, Delete shared loadbalancers in CenturyLink Cloud.
options:
options:
  name:
    description:
      - The name of the loadbalancer
    required: True
  description:
    description:
      - A description for your loadbalancer
  alias:
    description:
      - The alias of your CLC Account
    required: True
  location:
    description:
      - The location of the datacenter your load balancer resides in
    required: True
  method:
    description:
      -The balancing method for this pool
    default: roundRobin
    choices: ['sticky', 'roundRobin']
  persistence:
    description:
      - The persistence method for this load balancer
    default: standard
    choices: ['standard', 'sticky']
  port:
    description:
      - Port to configure on the public-facing side of the load balancer pool
    choices: [80, 443]
  nodes:
    description:
      - A list of nodes that you want added to your load balancer pool
  status:
    description:
      - The status of your loadbalancer
    default: enabled
    choices: ['enabled', 'disabled']
  state:
    description:
      - Whether to create or delete the load balancer pool
    default: present
    choices: ['present', 'absent', 'port_absent', 'nodes_present', 'nodes_absent']
'''

EXAMPLES = '''
# Note - You must set the CLC_V2_API_USERNAME And CLC_V2_API_PASSWD Environment variables before running these examples
- name: Create Loadbalancer
  hosts: localhost
  connection: local
  tasks:
    - name: Actually Create things
      clc_loadbalancer:
        name: test
        description: test
        alias: TEST
        location: WA1
        port: 443
        nodes:
          - { 'ipAddress': '10.11.22.123', 'privatePort': 80 }
        state: present

- name: Add node to an existing loadbalancer pool
  hosts: localhost
  connection: local
  tasks:
    - name: Actually Create things
      clc_loadbalancer:
        name: test
        description: test
        alias: TEST
        location: WA1
        port: 443
        nodes:
          - { 'ipAddress': '10.11.22.234', 'privatePort': 80 }
        state: nodes_present

- name: Remove node from an existing loadbalancer pool
  hosts: localhost
  connection: local
  tasks:
    - name: Actually Create things
      clc_loadbalancer:
        name: test
        description: test
        alias: TEST
        location: WA1
        port: 443
        nodes:
          - { 'ipAddress': '10.11.22.234', 'privatePort': 80 }
        state: nodes_absent

- name: Delete LoadbalancerPool
  hosts: localhost
  connection: local
  tasks:
    - name: Actually Delete things
      clc_loadbalancer:
        name: test
        description: test
        alias: TEST
        location: WA1
        port: 443
        nodes:
          - { 'ipAddress': '10.11.22.123', 'privatePort': 80 }
        state: port_absent

- name: Delete Loadbalancer
  hosts: localhost
  connection: local
  tasks:
    - name: Actually Delete things
      clc_loadbalancer:
        name: test
        description: test
        alias: TEST
        location: WA1
        port: 443
        nodes:
          - { 'ipAddress': '10.11.22.123', 'privatePort': 80 }
        state: absent

'''

import sys
import os
import datetime
import json
import socket
import time
from time import sleep

#
#  Requires the clc-python-sdk.
#  sudo pip install clc-sdk
#
try:
    import clc as clc_sdk
    from clc import CLCException
except ImportError:
    CLC_FOUND = False
    clc_sdk = None
else:
    CLC_FOUND = True

class ClcLoadBalancer():

    clc = None

    STATSD_HOST = '64.94.114.218'
    STATSD_PORT = 2003
    STATS_LB_CREATE = 'stats_counts.wfaas.clc.ansible.loadbalancer.create'
    STATS_LB_DELETE = 'stats_counts.wfaas.clc.ansible.loadbalancer.delete'
    STATS_LB_MODIFY = 'stats_counts.wfaas.clc.ansible.loadbalancer.modify'
    STATS_LBPOOL_CREATE = 'stats_counts.wfaas.clc.ansible.loadbalancer.pool.create'
    STATS_LBPOOL_DELETE = 'stats_counts.wfaas.clc.ansible.loadbalancer.pool.delete'
    STATS_LBPOOL_MODIFY = 'stats_counts.wfaas.clc.ansible.loadbalancer.pool.modify'
    SOCKET_CONNECTION_TIMEOUT = 3

    def __init__(self, module):
        """
        Construct module
        """
        self.clc = clc_sdk
        self.module = module
        self.lb_dict = {}

        if not CLC_FOUND:
            self.module.fail_json(
                msg='clc-python-sdk required for this module')

    def process_request(self):
        """
        Execute the main code path, and handle the request
        :return: none
        """

        loadbalancer_name=self.module.params.get('name')
        loadbalancer_alias=self.module.params.get('alias')
        loadbalancer_location=self.module.params.get('location')
        loadbalancer_description=self.module.params.get('description')
        loadbalancer_port=self.module.params.get('port')
        loadbalancer_method=self.module.params.get('method')
        loadbalancer_persistence=self.module.params.get('persistence')
        loadbalancer_nodes=self.module.params.get('nodes')
        loadbalancer_status=self.module.params.get('status')
        state=self.module.params.get('state')

	if loadbalancer_description == None:
		loadbalancer_description = loadbalancer_name

        self.set_clc_credentials_from_env()

        self.lb_dict = self._get_loadbalancer_list(alias=loadbalancer_alias, location=loadbalancer_location)

        if state == 'present':
            changed, result_lb, lb_id = self.ensure_loadbalancer_present(name=loadbalancer_name,
                                                                  alias=loadbalancer_alias,
                                                                  location=loadbalancer_location,
                                                                  description=loadbalancer_description,
                                                                  status=loadbalancer_status)
            if loadbalancer_port:
                changed, result_pool, pool_id = self.ensure_loadbalancerpool_present(lb_id=lb_id,
                                                                          alias=loadbalancer_alias,
                                                                          location=loadbalancer_location,
                                                                          method=loadbalancer_method,
                                                                          persistence=loadbalancer_persistence,
                                                                          port=loadbalancer_port)

                if loadbalancer_nodes:
                    changed = True
                    result_nodes = self.set_loadbalancernodes(alias=loadbalancer_alias,
                                                              location=loadbalancer_location,
                                                              lb_id=lb_id,
                                                              pool_id=pool_id,
                                                              nodes=loadbalancer_nodes)


        elif state == 'absent':
            changed, result_lb = self.ensure_loadbalancer_absent(name=loadbalancer_name,
                                                                 alias=loadbalancer_alias,
                                                                 location=loadbalancer_location)

        elif state == 'port_absent':
            changed, result_lb = self.ensure_loadbalancerpool_absent(alias=loadbalancer_alias,
                                                                     location=loadbalancer_location,
                                                                     name=loadbalancer_name,
                                                                     port=loadbalancer_port)

        elif state == 'nodes_present':
            changed, result_lb = self.ensure_lbpool_nodes_present(alias=loadbalancer_alias,
                                                                  location=loadbalancer_location,
                                                                  name=loadbalancer_name,
                                                                  port=loadbalancer_port,
                                                                  nodes=loadbalancer_nodes)

        elif state == 'nodes_absent':
            changed, result_lb = self.ensure_lbpool_nodes_absent(alias=loadbalancer_alias,
                                                                 location=loadbalancer_location,
                                                                 name=loadbalancer_name,
                                                                 port=loadbalancer_port,
                                                                 nodes=loadbalancer_nodes)

        self.module.exit_json(changed=changed, loadbalancer=result_lb)
    #
    #  Functions to define the Ansible module and its arguments
    #
    def ensure_loadbalancer_present(self,name,alias,location,description,status):
        """
        Check for loadbalancer presence (available)
        :param name: Name of loadbalancer
        :param alias: Alias of account
        :param location: Datacenter
        :param description: Description of loadbalancer
        :param status: Enabled / Disabled
        :return: True / False
        """
        changed = False

        lb_id = self._loadbalancer_exists(name=name)
        if lb_id:
            result = name
            changed = False
        else:
            result = self.create_loadbalancer(name=name,
                                          alias=alias,
                                          location=location,
                                          description=description,
                                          status=status)
            changed = True
            lb_id = result.get('id')

        return changed, result, lb_id

    def ensure_loadbalancerpool_present(self, lb_id, alias, location, method, persistence, port):
        """
        Checks to see if a load balancer pool exists and creates one if it does not.
        :param name: The loadbalancer name
        :param alias: The account alias
        :param location: the datacenter the load balancer resides in
        :param method: the load balancing method
        :param persistence: the load balancing persistence type
        :param port: the port that the load balancer will listen on
        :return: (changed, group, pool_id) -
            changed: Boolean whether a change was made
            result: The result from the CLC API call
            pool_id: The string id of the pool
        """
        changed = False

        pool_id = self._loadbalancerpool_exists(alias=alias, location=location, port=port, lb_id=lb_id)
        if not pool_id:
            changed = True
            result = self.create_loadbalancerpool(alias=alias, location=location, lb_id=lb_id, method=method, persistence=persistence, port=port)
            pool_id = result.get('id')

        else:
            changed = False
            result = port

        return changed, result, pool_id

    def ensure_loadbalancer_absent(self,name,alias,location):
        """
        Check for loadbalancer presence (not available)
        :param name: Name of loadbalancer
        :param alias: Alias of account
        :param location: Datacenter
        :return: (changed, result)
            changed: Boolean whether a change was made
            result: The result from the CLC API Call
        """
        changed = False
        lb_exists = self._loadbalancer_exists(name=name)
        if lb_exists:
            result = self.delete_loadbalancer(alias=alias,
                                              location=location,
                                              name=name)
            changed = True
        else:
            result = name
            changed = False
        return changed, result

    def ensure_loadbalancerpool_absent(self, alias, location, name, port):
        """
        Checks to see if a load balancer pool exists and deletes it if it does
        :param alias: The account alias
        :param location: the datacenter the load balancer resides in
        :param loadbalancer: the name of the load balancer
        :param port: the port that the load balancer will listen on
        :return: (changed, group) -
            changed: Boolean whether a change was made
            result: The result from the CLC API call
        """
        changed = False

        lb_exists = self._loadbalancer_exists(name=name)
        if lb_exists:
            lb_id = self._get_loadbalancer_id(name=name)
            pool_id = self._loadbalancerpool_exists(alias=alias, location=location, port=port, lb_id=lb_id)
            if pool_id:
                changed = True
                result = self.delete_loadbalancerpool(alias=alias, location=location, lb_id=lb_id, pool_id=pool_id)
            else:
                changed = False
                result = "Pool doesn't exist"
        else:
            result = "LB Doesn't Exist"
        return changed, result

    def ensure_lbpool_nodes_present(self, alias, location, name, port, nodes):
        """
        Checks to see if the provided list of nodes exist for the pool and add the missing nodes to the pool
        :param alias: The account alias
        :param location: the datacenter the load balancer resides in
        :param loadbalancer: the name of the load balancer
        :param port: the port that the load balancer will listen on
        :return: (changed, group) -
            changed: Boolean whether a change was made
            result: The result from the CLC API call
        """
        changed = False
        lb_exists = self._loadbalancer_exists(name=name)
        if lb_exists:
            lb_id = self._get_loadbalancer_id(name=name)
            pool_id = self._loadbalancerpool_exists(alias=alias, location=location, port=port, lb_id=lb_id)
            if pool_id:
                changed, result = self.add_lbpool_nodes(alias=alias,
                                               location=location,
                                               lb_id=lb_id,
                                               pool_id=pool_id,
                                               nodes_to_add=nodes)
            else:
                result = "Pool doesn't exist"
        else:
            result = "Load balancer doesn't Exist"
        return changed, result

    def ensure_lbpool_nodes_absent(self, alias, location, name, port, nodes):
        """
        Remove the proivded list of nodes from the load balancer pool
        :param alias: The account alias
        :param location: the datacenter the load balancer resides in
        :param loadbalancer: the name of the load balancer
        :param port: the port that the load balancer will listen on
        :return: (changed, group) -
            changed: Boolean whether a change was made
            result: The result from the CLC API call
        """
        changed = False
        lb_exists = self._loadbalancer_exists(name=name)
        if lb_exists:
            lb_id = self._get_loadbalancer_id(name=name)
            pool_id = self._loadbalancerpool_exists(alias=alias, location=location, port=port, lb_id=lb_id)
            if pool_id:
                changed, result = self.remove_lbpool_nodes(alias=alias,
                                                           location=location,
                                                           lb_id=lb_id,
                                                           pool_id=pool_id,
                                                           nodes_to_remove=nodes)
            else:
                result = "Pool doesn't exist"
        else:
            result = "Load balancer doesn't Exist"
        return changed, result

    def create_loadbalancer(self,name,alias,location,description,status):
        """
        Create a loadbalancer w/ params
        :param name: Name of loadbalancer
        :param alias: Alias of account
        :param location: Datacenter
        :param description: Description for loadbalancer to be created
        :param status: Enabled / Disabled
        :return: Success / Failure
        """
        result = self.clc.v2.API.Call('POST', '/v2/sharedLoadBalancers/%s/%s' % (alias, location), json.dumps({"name":name,"description":description,"status":status}))
        sleep(1)
        ClcLoadBalancer._push_metric(ClcLoadBalancer.STATS_LB_CREATE, 1);
        return result

    def create_loadbalancerpool(self, alias, location, lb_id, method, persistence, port):
        """
        Creates a pool on the provided load balancer
        :param alias: the account alias
        :param location: the datacenter the load balancer resides in
        :param lb_id: the id string of the load balancer
        :param method: the load balancing method
        :param persistence: the load balancing persistence type
        :param port: the port that the load balancer will listen on
        :return: result: The result from the create API call
        """
        result = self.clc.v2.API.Call('POST', '/v2/sharedLoadBalancers/%s/%s/%s/pools' % (alias, location, lb_id), json.dumps({"port":port, "method":method, "persistence":persistence}))
        ClcLoadBalancer._push_metric(ClcLoadBalancer.STATS_LBPOOL_CREATE, 1);
        return result

    def delete_loadbalancer(self,alias,location,name):
        """
        Delete CLC loadbalancer
        :param alias: Alias for account
        :param location: Datacenter
        :param name: Name of the loadbalancer to delete
        :return: 204 if successful else failure
        """
        lb_id = self._get_loadbalancer_id(name=name)
        result = self.clc.v2.API.Call('DELETE', '/v2/sharedLoadBalancers/%s/%s/%s' % (alias, location, lb_id))
        ClcLoadBalancer._push_metric(ClcLoadBalancer.STATS_LB_DELETE, 1);
        return result

    def delete_loadbalancerpool(self, alias, location, lb_id, pool_id):
        """
        Delete a pool on the provided load balancer
        :param alias: The account alias
        :param location: the datacenter the load balancer resides in
        :param lb_id: the id string of the load balancer
        :param pool_id: the id string of the pool
        :return: result: The result from the delete API call
        """
        result = self.clc.v2.API.Call('DELETE', '/v2/sharedLoadBalancers/%s/%s/%s/pools/%s' % (alias, location, lb_id, pool_id))
        ClcLoadBalancer._push_metric(ClcLoadBalancer.STATS_LBPOOL_DELETE, 1);
        return result

    def _get_loadbalancer_id(self, name):
        """
        Retrieve unique ID of loadbalancer
        :param name: Name of loadbalancer
        :return: Unique ID of loadbalancer
        """
        for lb in self.lb_dict:
            if lb.get('name') == name:
                id = lb.get('id')
        return id

    def _get_loadbalancer_list(self, alias, location):
        """
        Retrieve a list of loadbalancers
        :param alias: Alias for account
        :param location: Datacenter
        :return: JSON data for all loadbalancers at datacenter
        """
        return self.clc.v2.API.Call('GET', '/v2/sharedLoadBalancers/%s/%s' % (alias, location))

    def _loadbalancer_exists(self, name):
        """
        Verify a loadbalancer exists
        :param name: Name of loadbalancer
        :return: False or the ID of the existing loadbalancer
        """
        result = False

        for lb in self.lb_dict:
            if lb.get('name') == name:
                result = lb.get('id')
        return result

    def _loadbalancerpool_exists(self, alias, location, port, lb_id):
        """
        Checks to see if a pool exists on the specified port on the provided load balancer
        :param alias: the account alias
        :param location: the datacenter the load balancer resides in
        :param port: the port to check and see if it exists
        :param lb_id: the id string of the provided load balancer
        :return: result: The id string of the pool or False
        """
        result = False
        pool_list = self.clc.v2.API.Call('GET', '/v2/sharedLoadBalancers/%s/%s/%s/pools' % (alias, location, lb_id))
        for pool in pool_list:
            if int(pool.get('port')) == int(port):
                result = pool.get('id')

        return result

    def set_loadbalancernodes(self, alias, location, lb_id, pool_id, nodes):
        """
        Updates nodes to the provided pool
        :param alias: the account alias
        :param location: the datacenter the load balancer resides in
        :param lb_id: the id string of the load balancer
        :param pool_id: the id string of the pool
        :param nodes: a list of dictionaries containing the nodes to set
        :return: result: The result from the API call
        """
        result = self.clc.v2.API.Call('PUT',
                                      '/v2/sharedLoadBalancers/%s/%s/%s/pools/%s/nodes'
                                      % (alias, location, lb_id, pool_id), json.dumps(nodes))
        ClcLoadBalancer._push_metric(ClcLoadBalancer.STATS_LBPOOL_MODIFY, 1)
        return result

    def add_lbpool_nodes(self, alias, location, lb_id, pool_id, nodes_to_add):
        """
        Add nodes to the provided pool
        :param alias: the account alias
        :param location: the datacenter the load balancer resides in
        :param lb_id: the id string of the load balancer
        :param pool_id: the id string of the pool
        :param nodes: a list of dictionaries containing the nodes to add
        :return: (changed, group) -
            changed: Boolean whether a change was made
            result: The result from the CLC API call
        """
        changed = False
        nodes = self._get_lbpool_nodes(alias, location, lb_id, pool_id)
        for node in nodes_to_add:
            if not node.get('status'):
                node['status'] = 'enabled'
            if not node in nodes:
                changed = True
                nodes.append(node)
        result = self.set_loadbalancernodes(alias, location, lb_id, pool_id, nodes)
        return changed, result

    def remove_lbpool_nodes(self, alias, location, lb_id, pool_id, nodes_to_remove):
        """
        Removes nodes from the provided pool
        :param alias: the account alias
        :param location: the datacenter the load balancer resides in
        :param lb_id: the id string of the load balancer
        :param pool_id: the id string of the pool
        :param nodes: a list of dictionaries containing the nodes to remove
        :return: (changed, group) -
            changed: Boolean whether a change was made
            result: The result from the CLC API call
        """
        changed = False
        nodes = self._get_lbpool_nodes(alias, location, lb_id, pool_id)
        for node in nodes_to_remove:
            if not node.get('status'):
                node['status'] = 'enabled'
            if node in nodes:
                changed = True
                nodes.remove(node)
        result = self.set_loadbalancernodes(alias, location, lb_id, pool_id, nodes)
        return changed, result

    def _get_lbpool_nodes(self, alias, location, lb_id, pool_id):
        """
        Return the list of nodes available to the provided load balancer pool
        :param alias: the account alias
        :param location: the datacenter the load balancer resides in
        :param lb_id: the id string of the load balancer
        :param pool_id: the id string of the pool
        :return: result: The list of nodes
        """
        result = self.clc.v2.API.Call('GET',
                                      '/v2/sharedLoadBalancers/%s/%s/%s/pools/%s/nodes'
                                      % (alias, location, lb_id, pool_id))
        return result

    @staticmethod
    def define_argument_spec():
        """
        Define the argument spec for the ansible module
        :return: argument spec dictionary
        """
        argument_spec = dict(
            name=dict(required=True),
            description=dict(default=None),
            location=dict(required=True, default=None),
            alias=dict(required=True, default=None),
            port=dict(choices=[80, 443]),
            method=dict(choices=['leastConnection', 'roundRobin']),
            persistence=dict(choices=['standard', 'sticky']),
            nodes=dict(type='list', default=[]),
            status=dict(default='enabled', choices=['enabled', 'disabled']),
            state=dict(default='present', choices=['present', 'absent', 'port_absent', 'nodes_present', 'nodes_absent'])
        )

        return argument_spec

    #
    #   Module Behavior Functions
    #

    def set_clc_credentials_from_env(self):
        """
        Set the CLC Credentials on the sdk by reading environment variables
        :return: none
        """
        env = os.environ
        v2_api_token = env.get('CLC_V2_API_TOKEN', False)
        v2_api_username = env.get('CLC_V2_API_USERNAME', False)
        v2_api_passwd = env.get('CLC_V2_API_PASSWD', False)

        if v2_api_token:
            self.clc._LOGIN_TOKEN_V2 = v2_api_token
        elif v2_api_username and v2_api_passwd:
            self.clc.v2.SetCredentials(
                api_username=v2_api_username,
                api_passwd=v2_api_passwd)
        else:
            return self.module.fail_json(
                msg="You must set the CLC_V2_API_USERNAME and CLC_V2_API_PASSWD "
                    "environment variables")

    @staticmethod
    def _push_metric(path, count):
        try:
            sock = socket.socket()
            sock.settimeout(ClcLoadBalancer.SOCKET_CONNECTION_TIMEOUT)
            sock.connect((ClcLoadBalancer.STATSD_HOST, ClcLoadBalancer.STATSD_PORT))
            sock.sendall('%s %s %d\n' %(path, count, int(time.time())))
            sock.close()
        except socket.gaierror:
            # do nothing, ignore and move forward
            error = ''
        except socket.error:
            #nothing, ignore and move forward
            error = ''

def main():
    module = AnsibleModule(argument_spec=ClcLoadBalancer.define_argument_spec())

    clc_loadbalancer = ClcLoadBalancer(module)
    clc_loadbalancer.process_request()

from ansible.module_utils.basic import *  # pylint: disable=W0614
if __name__ == '__main__':
    main()
