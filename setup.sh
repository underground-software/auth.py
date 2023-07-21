#!/bin/bash
#
# basic setup of auth server
# initialize empty databases
sqlite3 users.db ".read users.default" ".exit"
sqlite3 sessions.db ".read sessions.default" ".exit"
