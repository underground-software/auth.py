DRY_RUN=""
NEW=""
while getopts "dn" OPTION; do
	case ${OPTION} in
		d)
			DRY_RUN=yes
			;;
		n)
			NEW=yes
			;;
		*)
			echo "unknown option"
			;;
	esac
done
shift $((OPTIND -1))

if [ ! -z "${NEW}" ]; then
	echo "(-n specified)"	
	CMD=`cat <<EOF
drop table if exists sessions;
create table sessions (
	token string PRIMARY KEY,
	user string UNIQUE NOT NULL,
	expiry string NOT NULL);
EOF`
	echo -e "RUNNING SQL: ${CMD}"
	OUT=`sqlite3 sessions.db "${CMD}"`
	echo -e "output: ${OUT}"

fi


CMD=`printf "select token, user, expiry from sessions;"`
OUT=""
echo -e "RUNNING SQL: ${CMD}"

if [ -z "${DRY_RUN}" ]; then
	OUT=`sqlite3 sessions.db "${CMD}"`
	echo -e "${OUT}"
else
	echo "DRY RUN (-d specified and no SQL run)"
fi
