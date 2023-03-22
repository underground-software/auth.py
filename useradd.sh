#!/bin/bash

# add user ${1} with password ${2} to users.db

DRY_RUN=""
FILE=
while getopts "df:" OPTION; do
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

if [ -z "${1}" ] || [ -z "${2}" ]; then
	echo "usage: $0 [USERNAME] [PASSWORD]"
	exit 1
fi

USERNAME=${1}
PWDHASH=`cat <<EOF | python3
import bcrypt
print(str(bcrypt.hashpw(b"${2}",bcrypt.gensalt()), "UTF-8"))
EOF`

# do_useradd: run the actual db addition
# $1: username
# $2: pwdhash
# $3: do dry run if nonempty
do_useradd() {
	USERNAME="${1}"
	PWDHASH="${2}"
	DRY_RUN="${3}"
	CMD=`printf "insert into users (username, pwdhash) values (\"%s\",\"%s\");" \
		"${USERNAME}" "${PWDHASH}"`
	echo -e "RUNNING SQL: ${CMD}"

	if [ -z "${DRY_RUN}" ]; then
		sqlite3 users.db "${CMD}"
	else
		echo "DRY RUN (-d specified and no SQL run)"
	fi

}

do_useradd "${USERNAME}" "${PWDHASH}" "${DRY_RUN}"
