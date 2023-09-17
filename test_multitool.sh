#!/bin/bash
#
# test multitool.sh

TESTS=(
"test_drop_session"
"test_create_session"
"test_validate_credentials"
"test_list_sessions"
"test_hash_password"
"test_new_user"
"test_delete_user"
"test_existence_check_user"
"test_list_roster_users"
"test_mutate_pwdhash_user"
)

COUNT_TOTAL=0
COUNT_PASSES=0

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

export ALT_DB_USERS='users.test.db'
export ALT_DB_SESSIONS='sessions.test.db'


M="report ${SCRIPT_DIR}/multitool.sh"
C0="-u x -p y"
C0="-u x -p x"
C2="-u y -p x"

report() {
		echo "EXEC '$@'"
		$@
}

announce() {
		echo "[${COUNT_TOTAL}] RUN ${1}"
}

test_check_session() {
		announce "${FUNCNAME[0]}"

		$M $C0 -n
		$M $C0 -c

		$M $C0 -s -t "${TOK}"
}

test_drop_session() {
		announce "${FUNCNAME[0]}"

		$M $C0 -n
		$M $C0 -c
		$M $C0 -d

}

test_create_session() {
		echo "${FUNCNAME[0]}: stub"

}

test_validate_credentials() {
		echo "${FUNCNAME[0]}: stub"
}

test_list_sessions() {
		echo "${FUNCNAME[0]}: stub"
}

test_hash_password() {
		echo "${FUNCNAME[0]}: stub"
}

test_new_user() {
		echo "${FUNCNAME[0]}: stub"
}

test_delete_user() {
		echo "${FUNCNAME[0]}: stub"
}

test_existence_check_user() {
		echo "${FUNCNAME[0]}: stub"
}

test_list_roster_users() {
		echo "${FUNCNAME[0]}: stub"
}

test_mutate_pwdhash_user() {
		echo "${FUNCNAME[0]}: stub"
}


refresh_testing_env() {
		# run tests on copies
		cp "${SCRIPT_DIR}/users.db" "${SCRIPT_DIR}/${ALT_DB_USERS}"
		cp "${SCRIPT_DIR}/sessions.db" "${SCRIPT_DIR}/${ALT_DB_SESSIONS}"
}

uwsgi --wsgi-file 'app.py' --http-socket ':8854' --pyargv 'test' 2>&1 >/dev/null &
PID=$!
export ALT_AUTH_SERVER='http://localhost:8854' 

for T in ${TESTS[@]}; do
		refresh_testing_env
		if $T; then
				echo -e "[PASS] $T"
				COUNT_PASSES=$((COUNT_PASSES + 1))
		else
				echo -e "[FAIL] $T"
		fi
		COUNT_TOTAL=$((COUNT_TOTAL + 1))
done


echo "TEST RESULTS: pass ${COUNT_PASSES}/${COUNT_TOTAL}"

kill $PID
