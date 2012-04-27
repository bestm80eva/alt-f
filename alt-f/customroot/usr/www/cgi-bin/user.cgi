#!/bin/sh

. common.sh
check_cookie
write_header "User script Setup"

CONF_MISC=/etc/misc.conf

if test -f "$CONF_MISC"; then
	. "$CONF_MISC"
fi

us=$(sed -n 's/USER_SCRIPT="\(.*\)"/\1/p' $CONF_MISC)
us=$(readlink -f "$us")
us=$(httpd -e "$us")

if test "$USER_LOGFILE" = "yes"; then
	log_chk="checked"
fi

cat<<-EOF
	<form id=user name=userf action=user_proc.cgi method="post">
	<table><tr>
	<td>Script to execute on powerup:</td>
	<td><input type=text name=user_script value="$us"></td>
	</tr>
	<tr><td>Create diagnostics file:</td>
	<td><input type=checkbox $log_chk name=create_log value="yes"></td></tr>
	<tr><td><br></td></tr>
	<tr><td></td><td>$(back_button)<input type=submit name=submit value="Submit"></td></tr>
	</table></form></body></html>
EOF

