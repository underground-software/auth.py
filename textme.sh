#!/bin/bash

MSG='ping from prod-01'
if [ ! -z "${1}" ]; then
	MSG="${1}"
fi

curl --get --data-urlencode "msg=${MSG}" localhost:6060
