#!/bin/bash

if [ ! -z "${1}" ]; then
	curl -H "Content-Type: application/x-www-form-urlencoded" \
		-X GET "127.0.0.1:9092/check?token="${1}
fi
