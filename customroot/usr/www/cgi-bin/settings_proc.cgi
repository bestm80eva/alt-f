#!/bin/sh

. common.sh
check_cookie

restart() {
	html_header
	busy_cursor_start

	hostname -f /etc/hostname >& /dev/null
	
	start-stop-daemon -K -x udhcpc >& /dev/null

	ifdown eth0 >& /dev/null
	sleep 1
	ifup eth0 >& /dev/null

	# FIXME: add 'reload' as 'restart' to all initscript services
	# that do not support reload and use 'rcall reload' instead
	# rcall restart >& /dev/null

	busy_cursor_end

	js_gotopage /cgi-bin/settings.cgi
	echo "</body></html>"
	exit 0
}

if test "${CONTENT_TYPE%;*}" = "multipart/form-data"; then
	upfile=$(upload_file)
	action="Upload"
else
	read_args
fi

#debug

case $action in

	SaveSettings)
		res=$(loadsave_settings -sf)
		if test $? = 1; then
			msg "$res"
		fi
		if test -f /tmp/firstboot; then
			rm -f /tmp/firstboot
			gotopage /cgi-bin/status.cgi
		fi
		;;

	ClearSettings)
		loadsave_settings -cf >& /dev/null
		;;

	LoadSettings)
		settings=$(httpd -d "$(echo $settings)")
		if test -n "$settings"; then
			loadsave_settings -lf "$settings"
			restart
		else
			msg "You must select a settings set."
		fi
		;;

	Upload)
		res=$(loadsave_settings -lf $upfile 2>&1 )
		st=$?
		rm -f $upfile
		if test $st != 0; then
			msg "$res"
		fi
		restart
		;;

	Download)
		downfile=$(loadsave_settings -cs)
		download_file /tmp/$downfile
		rm -f /tmp/$downfile
		exit 0
		;;
esac

#enddebug
gotopage /cgi-bin/settings.cgi


