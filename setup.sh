#!/bin/bash
#
# basic setup of auth server
# initialize empty databases

cd $(dirname $0)

echo "Setting up databases..."
sqlite3 users.db ".read users.default" ".exit"
sqlite3 sessions.db ".read sessions.default" ".exit"

echo "installing python requirements..."
pip install -r requirements.txt
