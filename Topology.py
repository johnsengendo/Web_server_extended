#! /usr/bin/env python3
# -*- coding: utf-8 -*-

# Importing required modules
import argparse
import os
import subprocess
import sys
import time
import threading

# Importing necessary functionalities from ComNetsEmu and Mininet
from comnetsemu.cli import CLI, spawnXtermDocker
from comnetsemu.net import Containernet, VNFManager
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.node import Controller

# Function to add web containers
def add_web_container(manager, name, role, image, shared_dir):
    return manager.addContainer(
        name, role, image, '', docker_args={
            'volumes': {
                shared_dir: {'bind': '/home/pcap/', 'mode': 'rw'}
            }
        }
    )

# Function to start the web server
def start_server():
    subprocess.run(['docker', 'exec', '-it', 'host_server', 'bash', '-c', 'cd /home && python3 Web_Server.py'])

# Function to start the web client
def start_client():
    subprocess.run(['docker', 'exec', '-it', 'browsing_client', 'bash', '-c', 'cd /home && python3 Web_Client.py'])

# Main execution starts here
if __name__ == '__main__':
    # Setting up command-line argument parsing
    parser = argparse.ArgumentParser(description='Web service with iperf test scenario.')
    parser.add_argument('--autotest', dest='autotest', action='store_const', const=True, default=False,
                        help='Enables automatic testing of the topology and closes the web app.')
    args = parser.parse_args()

    # Setting values for bandwidth and delay
    bandwidth = 10  # bandwidth in Mbps
    delay = 5       # delay in milliseconds
    autotest = args.autotest

    # Preparing a shared folder to store the pcap files
    script_directory = os.path.abspath(os.path.dirname(__file__))
    shared_directory = os.path.join(script_directory, 'pcap')

    # Creating the shared directory if it doesn't exist
    if not os.path.exists(shared_directory):
        os.makedirs(shared_directory)

    # Configuring the logging level
    setLogLevel('info')

    # Creating a network with Containernet (a Docker-compatible Mininet fork) and a virtual network function manager
    net = Containernet(controller=Controller, link=TCLink, xterms=False)
    mgr = VNFManager(net)

    # Adding a controller to the network
    info('*** Add controller\n')
    net.addController('c0')

    # Setting up Docker hosts as network nodes
    info('*** Creating hosts\n')
    h1 = net.addDockerHost('h1', dimage='dev_test', ip='10.0.0.1', docker_args={'hostname': 'h1'})
    h2 = net.addDockerHost('h2', dimage='dev_test', ip='10.0.0.2', docker_args={'hostname': 'h2'})
    h3 = net.addDockerHost('h3', dimage='dev_test', ip='10.0.0.3', docker_args={'hostname': 'h3'})
    h4 = net.addDockerHost('h4', dimage='dev_test', ip='10.0.0.4', docker_args={'hostname': 'h4'})
    h5 = net.addDockerHost('h5', dimage='dev_test', ip='10.0.0.5', docker_args={'hostname': 'h5'})
    h6 = net.addDockerHost('h6', dimage='dev_test', ip='10.0.0.6', docker_args={'hostname': 'h6'})

    # Adding switches and links to the network
    info('*** Adding switches and links\n')
    s1 = net.addSwitch('s1')
    s2 = net.addSwitch('s2')

    # Connecting hosts to switches
    net.addLink(h1, s1)
    net.addLink(h2, s1)
    net.addLink(h3, s1)
    net.addLink(h4, s2)
    net.addLink(h5, s2)
    net.addLink(h6, s2)

    # Connecting the switches with a link having bandwidth and delay
    middle_link = net.addLink(s1, s2, bw=bandwidth, delay=f'{delay}ms')

    # Starting the network
    info('\n*** Starting network\n')
    net.start()

    # Testing connectivity by pinging hosts
    info("*** Testing connectivity between h1 and h2\n")
    reply = h1.cmd("ping -c 5 10.0.0.2")
    print(reply)

    # Adding containers for web server and client
    web_server_host = net.addDockerHost(
    'host_server',
    dimage='web_server',
    ip='10.0.0.7',  # IP address for the web server
    docker_args={'hostname': 'host_server', 'volumes': {shared_directory: {'bind': '/home/pcap/', 'mode': 'rw'}}}
    )

    web_browser = net.addDockerHost(
    'browsing_client',
    dimage='web_client',
    ip='10.0.0.8',  # IP address for the web client
    docker_args={'hostname': 'browsing_client', 'volumes': {shared_directory: {'bind': '/home/pcap/', 'mode': 'rw'}}}
    )

    # Creating threads to run the server and client for web service
    server_thread = threading.Thread(target=start_server)
    client_thread = threading.Thread(target=start_client)

    # Starting the web server-client threads
    info('*** Starting web service communication between H1 and H2\n')
    server_thread.start()
    client_thread.start()

    # Introduce a 2-second delay before starting iperf communication
    time.sleep(2)

    # Starting iperf communication between H3 and H6
    info('*** Starting iperf communication between H3 and H6\n')
    iperf_server_thread = threading.Thread(
        target=lambda: net.get('h6').cmd('iperf -s &')  # Start iperf server on H6
    )
    iperf_client_thread = threading.Thread(
        target=lambda: net.get('h3').cmd('iperf -c 10.0.0.6 -t 5')  # Start iperf client on H3 for 5 seconds
    )

    iperf_server_thread.start()
    iperf_client_thread.start()

    # Wait for the iperf communication to finish
    iperf_client_thread.join()
    info('*** Iperf communication finished\n')

    # Stop the iperf server
    net.get('h6').cmd('pkill -f iperf')

    # Waiting for the server and client threads to finish
    server_thread.join()
    client_thread.join()
    info('*** Web service communication finished\n')

    # If not in autotest mode, start an interactive CLI
    if not autotest:
        CLI(net)

    # Cleanup: removing containers and stopping the network and VNF manager
    mgr.removeContainer('host_server')
    mgr.removeContainer('browsing_client')
    net.stop()
    mgr.stop()
