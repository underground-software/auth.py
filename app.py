from urllib.parse import parse_qs
from html import escape
from http import cookies
import sys, datetime, bcrypt, sqlite3, hashlib, random
from subprocess import run, PIPE

from config import SESSIONS_DB, USERS_DB,\
	TXT_ALERT, LOG_ALERT, ALERT_LOGFILE,\
	SESSION_DAYS, SESSION_MINS, NEW_SESSION_BUMPS_OLD

from orbit import appver, messageblock, ROOT, DP

# FYI: SR means "start response": it's the function
#	called to start the http response
# FYI: US means "user session": it's used whenever
#	we are dealing with user session info

FORM_LOGIN="""
	<form id="login" method="post" action="/login">
		<label for="username">Username:<br /></label>
		<input name="username" type="text" id="username" />
	<br />
		<label for="password">Password:<br /></label>
		<input name="password" type="password" id="password" />
	<br />
		<button type="submit">Submit</button>
	</form>
"""

FORM_LOGOUT="""
	<div class="logout_info">
	<div class="logout_left">
	<table>
	<tr>
		<th>Cookie Key</th>
		<th>Value</th>
	</tr>
	<tr>
		
		<td>Token</td>
		<td>%(token)s</td>
	</tr>
	<tr>
		
		<td>Username</td>
		<td>%(username)s</td>
	</tr>
	<tr>
		
		<td>Expiry</td>
		<td>%(expiry)s</td>
	</tr>
	<tr>
		
		<td>Remaining</td>
		<td>%(remaining)s</td>
	</tr>
	</table>
	</div>

	<div class="logout_right">

	<div class="logout_right_inner">

	<h5> Secure Pages </h5>
	<ul>
	<li>
	<a href="/US">Home</a>
	</li>
	<li>
	<a href="/terminal">Terminal</a>
	</li>
	</ul>
	</div>
	</div>
	</div>

	<div class="logout_buttons">
	%(logout_button)s
	</div>
"""	

FORM_LOGOUT_EXTERNAL="""
	<form id="logout" method="post" action="/login/logout.md">
		<button type="submit">Logout</button>
	</form>
"""

FORM_LOGOUT_INTERNAL="""
	<form id="logout" method="get" action="/login">
		<input type="hidden" name="logout" value="true">
		<button type="submit" class="logout">Logout</button>
	</form>
	<form id="renew" method="get" action="/login">
		<input type="hidden" name="renew" value="true">
		<button type="submit" class="renew">Renew</button>
	</form>
"""

def session_enum():
	session_enum.cnt += 1
	return session_enum.cnt
session_enum.cnt = 0

# data = (token,..)
SESSION_GET_TOKEN=session_enum()
SESSION_GET_TOKEN_COMM="SELECT token, user, expiry FROM sessions WHERE token = \"%s\";"

# data = (...,user,...)
SESSION_GET_USER=session_enum()
SESSION_GET_USER_COMM="SELECT token, user, expiry FROM sessions WHERE user= \"%s\";"

# data = (token, user, expiry)
SESSION_NEW=session_enum()
SESSION_NEW_COMM="INSERT INTO sessions (token, user, expiry) VALUES (\"%s\", \"%s\", \"%s\");"

# data = (token,..)
SESSION_DROP_TOKEN=session_enum()
SESSION_DROP_TOKEN_COMM = "DELETE FROM sessions WHERE token = \"%s\";"

# data = (...,user,...)
SESSION_DROP_USER=session_enum()
SESSION_DROP_USER_COMM = "DELETE FROM sessions WHERE user = \"%s\";"

def _do_sessions_comm(comm, commit=False, fetch=False):
	return do_sqlite3_comm(SESSIONS_DB, comm, commit=commit, fetch=fetch)


def do_sessions_comm(comm, US=None):
	if	 comm == SESSION_NEW:
		return _do_sessions_comm(SESSION_NEW_COMM % US, commit=True)
	elif comm == SESSION_GET_TOKEN:
		return _do_sessions_comm(SESSION_GET_TOKEN_COMM % (US_token(US)), fetch=True)
	elif comm == SESSION_GET_USER:
		return _do_sessions_comm(SESSION_GET_USER_COMM % (US_user(US)), fetch=True)
	elif comm == SESSION_DROP_TOKEN:
		return _do_sessions_comm(SESSION_DROP_TOKEN_COMM % (US_token(US)), commit=True)
	elif comm == SESSION_DROP_USER:
		return _do_sessions_comm(SESSION_DROP_USER_COMM % (US_user(US)), commit=True)
	else:
		DP("unknown sessions comm type")
		return None	

def ALERT(msg):
	# this will be temporarily broken before this part is automated
	if TXT_ALERT:
		m = '%s: %s' % (appver(), msg)
		o = run(['./textme.sh', m], stdout=PIPE, stderr=PIPE)
		DP(o)
	if LOG_ALERT:
		t = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S GMT')
		o ='log %s' % msg
		m = '[%s] %s' % (t, msg)
		try:
			with open(ALERT_LOGFILE, 'a') as f:
				print(m, file=f)
		except Exception as e:
			o += '\n%s' % str(e)
		DP(o)


# Source: https://stackoverflow.com/questions/14107260/set-a-cookie-and-retrieve-it-with-python-and-wsgi
def set_cookie_header(name, value, days=SESSION_DAYS, minutes=SESSION_MINS):
	dt = datetime.datetime.now() + datetime.timedelta(days=days,minutes=minutes)
	fdt = dt.strftime('%a, %d %b %Y %H:%M:%S GMT')
	secs = 60 * minutes + 86400 * days
	return ('Set-Cookie', '{}={}; Expires={}; Max-Age={}; Path=/'.format(name, value, fdt, secs))

# US (user session data) structure (token, user, expiry)
def US_token(US):
	return US[0]

def US_user(US):
	return US[1]

def US_expiry(US):
	return US[2]

def US_expired(US):
	if US_expiry(US) is None:
		return None
	if datetime.datetime.utcnow().timestamp() > US_expiry(US):
		DP('US expired')
	else:
		DP('US unexpired')
	return datetime.datetime.utcnow().timestamp() > US_expiry(US)

def mkUS(token=None, user=None, expiry=None):
	return (token, user, expiry) 

def DP(string):
	return print(string, file=sys.stderr)

# shortand for bytes(string, "UTF-8")
def bytes8(string):
	return bytes(string, "UTF-8")

# shortand for str(string, "UTF-8")
def str8(string):
	return str(string, "UTF-8")

def do_sqlite3_comm(db, comm, commit=False, fetch=False):
	result=None
	db_con = sqlite3.connect(db)
	db_cur0 = db_con.cursor()
	
	DP("RUN SQL: %s" % comm)
	db_cur1 = db_cur0.execute(comm)

	if fetch:
		result=db_cur1.fetchone()
		DP("SQL RES: %s" % str(result))

	if commit:
		DP("RUN SQL: COMMIT;")
		db_cur2 = db_cur1.execute("COMMIT;")

	db_con.close()

	return result

def new_session_by_username(session_username):
	
	ALERT('start session for user %s ' % session_username)
	
	if get_session_by_username(session_username) is not None:
		# If there is an existing sesion open, drop the old session
		if NEW_SESSION_BUMPS_OLD:
			drop_session_by_username(session_username)
		# If there is an existing sesion open, don't let the new one start
		else:
			return None

	# Make a session_token out of sha256(username + time + random string)
	session_token = hashlib.sha256(bytes8(session_username \
		+ str(datetime.datetime.now())) \
		+ bytes8(''.join(random.choices("ABCDEFGHIJ",k=10)))).hexdigest()

	# sessions expire in SESSION_DAYS * 24 * 60 + SESSION_MINS minutes for now
	session_expiry = (datetime.datetime.utcnow() + datetime.timedelta(minutes=SESSION_MINS, days=SESSION_DAYS)).timestamp()

	do_sessions_comm(SESSION_NEW, mkUS(token=session_token, \
		user=session_username, expiry=session_expiry))

	return get_session_by_username(session_username)

def drop_session_by_username(session_username):
	do_sessions_comm(SESSION_DROP_USER, mkUS(user=session_username))
	return

def drop_session_by_token(session_token):
	do_sessions_comm(SESSION_DROP_TOKEN, mkUS(token=session_token))
	return

def get_session_by_username(session_username):
	US = do_sessions_comm(SESSION_GET_USER, mkUS(user=session_username))
	if US is None:
		return None	

	# if the current timestamp is greater than session expiry,
	# purge the old session from the databse and return none 
	# by re-trying the request
	if US_expired(US):
		DP('drop by username %s' % session_username)
		drop_session_by_username(session_username)
		return get_session_by_username(session_username)

	return US

# return none if token is expired and also purge old entry
def get_session_by_token(session_token):
	US = do_sessions_comm(SESSION_GET_TOKEN, mkUS(token=session_token))
	if US is None:
		return None	

	# if the current timestamp is greater than session expiry,
	# purge the old session from the databse and return none 
	# by re-trying the request
	if US_expired(US):
		DP('drop by token %s' % session_token)
		drop_session_by_token(session_token)
		return get_session_by_token(session_token)
	return US

def ok_html(doc, SR, extra_docs=[], extra_headers=[]):
	SR('200 OK', [('Content-Type', 'text/html')] + extra_headers)
	return [bytes8(doc)] + [bytes8(d) for d in extra_docs]

def ok_text(text, SR, extra_text=[], extra_headers=[]):
	SR('200 OK', [('Content-Type', 'text/plain')] + extra_headers)
	return [bytes8(text)] + [bytes8(t) for t in extra_text]

def ok_urlencoded(content, SR, extra_content=[], extra_headers=[]):
	SR('200 OK', [('Content-Type', 'application/x-www-form-urlencoded')] + extra_headers)
	return [bytes8(content)] + [bytes8(c) for c in extra_content]

def unauth_urlencoded(content, SR):
	SR('401 Unauthorized', [('Content-Type', \
		'application/x-www-form-urlencoded')])
	return [bytes8(content)]

def notfound_urlencoded(content, SR):
	SR('404 Not Found', [('Content-Type', \
		'application/x-www-form-urlencoded')])
	return [bytes8(content)]
	
def _handle_check(token, SR):
	US = get_session_by_token(token)

	if US is not None:
		username = US_user(US)
		# include authorized username in HTTP headers
		return ok_urlencoded(username, SR,
			extra_headers=[('X-Auth-User', username)])
	else:
		return unauth_urlencoded('null', SR)

def handle_check(queries, SR):
	token = queries.get('token',[''])[0]
	if len(token) > 0:
		return _handle_check(token, SR)
	else:
		return unauth_urlencoded('error="No token= supplied in URL. Nothing done."', SR)

def _handle_logout(username, SR):
	US = get_session_by_username(username)

	# see comment in handle_check()
	if US is not None:
		drop_session_by_username(username)
		return ok_urlencoded(username, SR)
	else:
		return notfound_urlencoded('null', SR)

def handle_logout(queries, SR):
	username = queries.get('username',[''])[0]
	if len(username) > 0:
		return _handle_logout(username, SR)
	else:
		return ok_urlencoded('error="No username= suplied in URL. Nothing done."', SR)

def get_req_body_size(env):
	try:
		req_body_size = int(env.get('CONTENT_LENGTH', 0))
	except ValueError:
		req_body_size = 0
	
	return req_body_size

def is_post_req(env):
	return get_req_body_size(env) > 0


def get_pwdhash_by_user(username):
	comm="select pwdhash from users where username = \"%s\";" % username

	result=do_sqlite3_comm(USERS_DB, comm, fetch=True)
	if result is not None:
		result = result[0]

	return result

# NOTE: Usage of any password in plaintext outside of this function is a bug
def check_credentials(username, password):
	pwdhash=get_pwdhash_by_user(username)
	ret = pwdhash is not None and bcrypt.checkpw(bytes8(password), bytes8(pwdhash))
	if ret:
		DP(f'[AUTHENTICATED] Correct password for {username}')
	else:
		DP(f'Incorrect password for {username}')

	return ret

CREDS_OK	= 0
CREDS_CONFLICT	= 1
CREDS_BAD	= 2
def login_creds_from_body(env):
	US=None
	username=''
	status = CREDS_BAD
	req_body_size= get_req_body_size(env)

	if (req_body_size > 0):
		req_body = env['wsgi.input'].read(req_body_size) 
		data = parse_qs(req_body)

		# get actual urlencoded body content
		username = escape(str8(data.get(bytes8('username'), [b''])[0]))
		password = escape(str8(data.get(bytes8('password'), [b''])[0]))
		quiet = escape(str8(data.get(bytes8('quiet'), [b'NO'])[0])) == "yes"

		if check_credentials(username, password):
			# if the password is valid,
			# try to start a new session right away
			US = new_session_by_username(username)
			# session for $username already exists if we still get None
			status = CREDS_CONFLICT if US is None else CREDS_OK

	if status == CREDS_CONFLICT:
		US = mkUS(user=username)

	return [US, status, quiet]

def renew_session(US):
	# refresh US
	US = get_session_by_token(US_token(US))

	# if it's gone, dont dropt it
	if US:
		drop_session_by_token(US_token(US))

	# if the token is not expired, issue a new one
	if US and not US_expired(US):
		US = new_session_by_username(US_user(US))

	return US

def get_session_from_cookie(env):
	US=None

	# get auth=$TOKEN from user cookie
	cookie_user_raw = env.get('HTTP_COOKIE', '')
	cookie_user = cookies.BaseCookie('')
	cookie_user.load(cookie_user_raw)

	auth = cookie_user.get('auth', cookies.Morsel())
	if auth.value is not None:
		US = get_session_by_token(auth.value)

	return US	

def quietly_generate_token_plaintext(SR, US):
	SR('200 Ok', [('Content-Type', 'text/plain')])
	return bytes8(US_token(US) if US is not None else "null")


def generate_page_login(form, SR, extra_headers, msg, logged_in=False):
	base=''

	nav = ROOT + '/data/header'
	with open(nav, 'r') as f:
		base += f.read()

	base += form 

	extra = messageblock([('message', msg), ('appver', appver())])

	return ok_html(base, SR, extra_docs=extra, extra_headers=extra_headers)

def check_logout(queries):
	return queries.get('logout', '') == ['true']

def check_renew(queries):
	return queries.get('renew', '') == ['true']

def build_login_form_html(SR, US, msg, extra_headers):
	# default to login form unless we have a valid user_session
	main_form = FORM_LOGIN
	if US:
		expiry_dt = datetime.datetime.fromtimestamp(US_expiry(US))
		main_form = FORM_LOGOUT  % {
			'token' : US_token(US),
			'username' : US_user(US),
			'expiry' : expiry_dt.strftime('%a, %d %b %Y %H:%M:%S GMT'),
			'remaining' : str(expiry_dt - datetime.datetime.utcnow()),
			'logout_button' : FORM_LOGOUT_INTERNAL
		}

	return generate_page_login(main_form, SR, extra_headers, msg, logged_in=US is not None)
		
def handle_login(queries, SR, env):
	msg='welcome, please login'
	
	# put cookie in here to set user cookie
	extra_headers = []

	# check if user $TOKEN valid and authenticate as $USERNAME
	US = get_session_from_cookie(env)
	if US:
		username = US_user(US)
		# check if user requests logout
		if check_logout(queries):
			DP('logout initiated for %s' % username)
			drop_session_by_username(username)
			# clear local cookie on logout
			extra_headers.append(set_cookie_header("auth", ""))
			msg = 'logged out %s successfully' % username
			US = None
		elif check_renew(queries):
			DP('renew initiated for %s' % username)
			US = renew_session(US)
			if US is not None:
				msg = 'renewed session for %s' % username
				extra_headers.append(set_cookie_header("auth", US_token(US)))
			else:
				msg = 'failed to renew session for %s' % username 
		else:
			msg = 'you are logged in as %s' % username
	
	# if not already logged in from cookie and if posting credentials
	login_status=None
	# quiet option enables automation to post a username and password
	# in exchange for a plaintext valid sesssion token in isolation
	quiet=False
	if US is None and is_post_req(env):
		# attempt to login using credentials from body
		[US, login_status, quiet] = login_creds_from_body(env)
	

	# we made an attemmpt to login, handle the login response
	if login_status is not None:
		if login_status == CREDS_BAD:
			msg = 'incorrect login'
		elif login_status == CREDS_CONFLICT:
			msg = 'existing open session for user %s' % US_user(US)
			# US only contains the username when creds conflict
			# to create this message. Now we clear it to normalize logic
			US=None
		elif login_status == CREDS_OK:
			msg = 'start new session for user %s' % US_user(US)
			# we just logged in as $USERNAMAE
			extra_headers.append(set_cookie_header("auth", US_token(US)))

	if quiet:
		return quietly_generate_token_plaintext(SR, US)
	else:
		return build_login_form_html(SR, US, msg, extra_headers)

def handle_mail_auth(SR, env):
	username = env.get('HTTP_AUTH_USER', '')
	password = env.get('HTTP_AUTH_PASS', '')
	protocol = env.get('HTTP_AUTH_PROTOCOL', '')
	method = env.get('HTTP_AUTH_METHOD', '')
	#this should be impossible if nginx is configured properly
	if not username or not password or protocol not in ('smtp', 'pop3') or method != 'plain':
		SR('400 Bad Request', [('Auth-Status', 'Invalid Request')])
		return ''
	if not check_credentials(username, password):
		#even for incorrect credentials we are to use 200 OK
		SR('200 OK', [('Auth-Status', 'Invalid Credentials')])
		return ''
	comm="select lfx from users where username = \"%s\";" % username
	(lfx,) = do_sqlite3_comm(USERS_DB, comm, fetch=True)
	SR('200 OK', [('Auth-Status', 'OK'), ('Auth-Server', '127.0.0.1'), (('Auth-Port', '1465' if protocol == 'smtp' else '1995') if not lfx else ('Auth-Port', '1466' if protocol == 'smtp' else '1996'))])
	return ''

def application(env, SR):

	path_info = env.get("PATH_INFO", "")
	query_string = env.get("QUERY_STRING", "")
	queries = parse_qs(query_string)

	if len(sys.argv) > 1:
		match sys.argv[1]:
			case 'test':
				USERS_DB = 'users.test.db'
				SESSIONS_DB = 'sessions.test.db'
			case _:
				pass

	DP("New request: path_info=\"%s\", queries=\"%s\"" \
		% (str(path_info), str(queries)))

	if path_info == "/login":
		return handle_login(queries, SR, env)
	elif path_info == "/check":
		return handle_check(queries, SR)
	elif path_info == "/logout":
		return handle_logout(queries, SR)
	elif path_info == "/mail_auth":
		return handle_mail_auth(SR, env)
	else:
		return notfound_urlencoded('error="Page not found."', SR)
