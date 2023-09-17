#!/bin/bash
#
# multitool.sh: multipurpose script to manage users
# and sessions of the auth.py backend
#
# features (added as they are developed):
# - change password for a user
# - list users
# - check whether a user exists
# - delete a user
# - add user & pass
# - validate a user & pass pair
# - list sessions
# - logout a user from their current session 
# possible extensions:
# - make database references path generic
# - run from ExecutionConfig

usage() {
	echo "usage of $(basename $0):"
	echo "no argument: list active user sessions"
	echo " -d: drop existing session for user"
	echo " -c: create session for user and get token"
	echo " -v: validate a username and password pair"
	echo " -n: create new user with supplied password"
	echo " -w: delete (\"withdraw\") user from database"
	echo " -r: list all users (\"roster\")"
	echo " -i: increased information (more verbose output)"
	echo " -u <user>: specify a username to be used"
	echo " -p <pass>: specify a password to be used"
}

VERBOSE=
Echo() {
	if [ "${VERBOSE}" == "yes" ]; then
		echo -e $@
	fi
}

die() {
	echo -e "error: ${1}" > /dev/stderr
	exit 1
}

do_drop_session() {
	URI="${AUTH_SERVER}/logout?username=${USER}"
	HEADERS="Content-Type: application/x-www-form-urlencoded"
	echo "GET ${URI} HTTP/1.1"
	curl -H "${HEADERS}" -X GET "${URI}"
}

do_create_session() {
	URI="${AUTH_SERVER}/login"
	BODY="username=${USER}&password=${PASS}&quiet=YES"

	echo "POST ${URI} body: [${BODY}] HTTP/1.1"
	curl -d "${BODY}" -X POST "${URI}" -c token
	echo
}

need_username_or_die() {
	test -z "${USER}" && die "no username supplied"
}

need_password_or_die() {
	test -z "${PASS}" && die "no password supplied"
}

need_credentials_or_die() {
	need_username_or_die
	need_password_or_die
}

do_validate_credentials() {
	URI="${AUTH_SERVER}/check?username=${USER}"

	need_credentials_or_die

	CMD="SELECT pwdhash FROM users WHERE username = '${USER}';"
	Echo -e "Running sqlite command on $(basename "${DB_USERS}"): '${CMD}'"

	HASH=`sqlite3 "${DB_USERS}" "${CMD}"`

	Echo "Hash from $(basename "${DB_USERS}"): '${HASH}'"

	# if $HASH is empty,
	# then $USER does not exist
	# therefore jump to invalid caase
	if [ -z "${HASH}" ]; then
		echo "null"
		return 1
	fi

	VALID=$(cat <<EOF | python3
import bcrypt
if bcrypt.checkpw(b'${PASS}', b'${HASH}'):
	print("${USER}")
else:
	print("null")
EOF
	)

	echo "${VALID}"

	if [ "${VALID}" == "null" ]; then
		return 1
	fi
}

do_list_sessions() {
	CMD="SELECT token, user, expiry FROM sessions;"
	Echo -e "Running sqlite command on $(basename "${DB_SESSIONS}") '${CMD}'"
	OUT=`sqlite3 "${DB_SESSIONS}" "${CMD}"`
	echo -e "${OUT}"
}

do_hash_password() {
	need_password_or_die

	PWDHASH=$(cat <<EOF | python3
from bcrypt import hashpw, gensalt
print(str(hashpw(b"${PASS}", gensalt()), "UTF-8"))
EOF
	)

	if [ -z ${PWDHASH} ]; then
		die "unable invoke bcrypt hash function"
	fi

	echo "${PWDHASH}"
}

do_new_user() {
	need_credentials_or_die

	PWDHASH=$(do_hash_password)

	Echo "OK: hashpw(${PASS}, gensalt())=${PWDHASH}"

	CMD="INSERT INTO users (username, pwdhash) VALUES ('${USER}', '${PWDHASH}');"

	Echo -e "Running sqlite command on $(basename "${DB_USERS}") '${CMD}'"

	if sqlite3 "${DB_USERS}" "${CMD}" 2>& 1 | grep "UNIQUE constraint failed" > /dev/null; then
		die "username '${USER}' taken"
	fi

	# save and restore verbosity
	# since within this call we strictly want the main output
	PUSH_VERBOSE=${VERBOSE}
	VERBOSE='no'
	valid=$(do_validate_credentials)
	VERBOSE=${PUSH_VERBOSE}

	if [ "${valid}" != "${USER}" ]; then
		die "failed to add user ${USER}"
	else
		echo "credentials = { username: ${USER}, password: ${PASS} }"
	fi
}

# delete sam, sa, sa2, sa3 sa4 a5

do_delete_user() {
	need_username_or_die

	if ! do_existence_check_user > /dev/null; then
		echo "null"
		return 1
	fi

	CMD="DELETE FROM users WHERE username = '${USER}';"

	Echo -e "Running sqlite command on $(basename "${DB_USERS}") '${CMD}'"

	if ! sqlite3 "${DB_USERS}" "${CMD}"; then
		die "failed to delete user '${USER}'"
	fi

	echo "${USER}"
}

do_existence_check_user() {
	need_username_or_die

	CMD="SELECT pwdhash FROM users WHERE username = '${USER}';"
	PWDHASH=$(sqlite3 "${DB_USERS}" "${CMD}")

	# if we lookup a password in the database for $USER and find nothing
	# then the user does not exist
	if [ -z "${PWDHASH}" ]; then
		echo "null"
		return 1

	else
		echo "${USER}"
	fi

}

do_list_roster_users() {
	CMD="SELECT id, username, pwdhash FROM users;"
	Echo -e "Running sqlite command on $(basename "${DB_USERS}"): '${CMD}'"
	OUT=`sqlite3 "${DB_USERS}" "${CMD}"`
	echo -e "${OUT}"
	
}

do_mutate_pwdhash_user() {
	need_credentials_or_die


	if ! do_existence_check_user > /dev/null; then
		die "cannot change password of nonexistent user '${USER}'"
	fi

	PWDHASH=$(do_hash_password)

	CMD="UPDATE users SET pwdhash = '${PWDHASH}' WHERE username = '${USER}'"
	Echo -e "Running sqlite command on $(basename "${DB_USERS}"): '${CMD}'"
	sqlite3 "${DB_USERS}" "${CMD}"

	echo "credentials = { username: ${USER}, password: ${PASS} }"
}


# from: https://stackoverflow.com/questions/59895/how-do-i-get-the-directory-where-a-bash-script-is-located-from-within-the-script
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# configuration defaults
USER=
PASS=
# default naked invocation to list all known sessions
OP="list_sessions"
# use snippet to pull the IP:port text string from the orbit.py
# generated by cano.py
AUTH_SERVER=$(${SCRIPT_DIR}/get_auth_server.py)

while getopts "f:minawehdbcvru:p:" X; do
	case ${X} in
		i)
			VERBOSE='yes'
			;;
		b)
			OP="hash_password"
			;;
		n)
			OP="new_user"
			;;
		w)
			OP="delete_user"
			;;
		e)
			OP="existence_check_user"
			;;
		d)
			OP="drop_session"
			;;
		c)
			OP="create_session"
			;;
		v)
			OP="validate_credentials"
			;;
		r)
			OP="list_roster_users"
			;;
		m)
			OP="mutate_pwdhash_user"
			;;
		u)
			USER=${OPTARG}
			;;
		p)
			PASS=${OPTARG}
			;;
		h)
			usage
			;;
		*)
			usage
			;;
	esac
done
shift $(($OPTIND - 1))

# We need to make sure all database calls are local to this repo
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

DB_USERS="${SCRIPT_DIR}/users.db"
DB_SESSIONS="${SCRIPT_DIR}/sessions.db"


Echo "ExecutionConfig = {"
Echo "\toperation: '${OP}'"
Echo "\tusername: '${USER}'"
Echo "\tpassword: '${PASS}'"
Echo "\tdb_users: '${DB_USERS}'"
Echo "\tdb_sessions: '${DB_SESSIONS}'"
Echo "}"

do_${OP}
