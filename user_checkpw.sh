#!/bin/bash
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
PASSWORD=${2}

RESULT="no"
# do_checkpw: check password
do_checkpw() {
	cat <<EOF | python3
import bcrypt
if bcrypt.checkpw(b'${1}', b'${2}'):
	print("yes")
EOF
}

# do_user_checkpw: get user pwdhash and check password
# $1: username
# $2: do dry run if nonempty
do_user_checkpw() {
	USERNAME="${1}"
	DRY_RUN="${2}"
	CMD=`printf "select pwdhash from users where username = (\"%s\");" "${USERNAME}"`
	echo -e "RUNNING SQL: ${CMD}"

	if [ -z "${DRY_RUN}" ]; then
		HASH=`sqlite3 users.db "${CMD}"`
	else
		echo "DRY RUN (-d specified and no SQL run)"
	fi

	if [ ! -z "${HASH}" ]; then
		OUTPUT=$(do_checkpw "${PASSWORD}" "${HASH}")
	fi

	if [ ! -z "${OUTPUT}" ]; then
		echo "valid"
	fi
	
}

do_user_checkpw "${USERNAME}" "${DRY_RUN}"
