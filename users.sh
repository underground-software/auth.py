#!/bin/bash

# show users in userdb

DRY_RUN=""
while getopts "d" OPTION; do
	case ${OPTION} in
		d)
			DRY_RUN=yes
			;;
		*)
			echo "unknown option"
			;;
	esac
done
shift $((OPTIND -1))

CMD=`printf "select id, username, pwdhash from users;"`
OUT=""
echo -e "RUNNING SQL: ${CMD}"

if [ -z "${DRY_RUN}" ]; then
	OUT=`sqlite3 users.db "${CMD}"`
	echo -e "${OUT}"
else
	echo "DRY RUN (-d specified and no SQL run)"
fi
