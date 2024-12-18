#!/bin/bash

# Updating package lists
apt-get update -y

# Installing useful tools
apt-get install -y --no-install-recommends \
    bash \
    python3 \
    python3-pip \
    bash-completion \
    curl \
    net-tools
    
# Install Python packages
pip install requests

# Installing the packages required e.g for dumping traffic
apt-get install -y \
    tcpdump \
    nano

