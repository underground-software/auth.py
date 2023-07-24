#!/bin/bash

# basic setup of auth server

# change directory to the location of this script
cd $(dirname $0)

# initialize empty databases
sqlite3 users.db ".read users.default" ".exit"
sqlite3 sessions.db ".read sessions.default" ".exit"

# install python dependencies
pip install -r requirements.txt
