#!/bin/bash

if [ ! -z "${1}" ]; then
	uwsgi_curl  \
		-H "Content-Type: application/x-www-form-urlencoded" \
		-X GET 127.0.0.1:9090 \
		"/check?token="${1}
fi
