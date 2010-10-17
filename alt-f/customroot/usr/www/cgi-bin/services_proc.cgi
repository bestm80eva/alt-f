#!/bin/sh

# start_stop service action
start_stop() {
	local serv act
	serv=$1
	act=$2

	sscript=/etc/init.d/S??$serv
	if test -n "$sscript"; then    
		if test "$act" = "enable"; then
			chmod +x $sscript
			touch $sscript
		elif test "$act" = "disable"; then
			chmod -x $sscript
			touch $sscript
		fi

		if test "$act" = "start" -o "$act" = "enable"; then
			res=$(sh $sscript start)
			if test $? = 1; then
				scp=$(basename $sscript)
				msg "${scp:3}: $res"
			fi
		elif test "$act" = "stop" -o "$act" = "disable"; then
			sh $sscript stop >& /dev/null
			for i in $(seq 1 50); do
				if ! sh $sscript status >& /dev/null; then
					break
				fi	
				usleep 200000
			done
		fi
	fi
}

. common.sh
read_args
check_cookie

#debug

if test -n "$Submit"; then

	srvs="$(httpd -d $Submit)"
	for i in $srvs; do
		st=$(eval echo \$$i)
		if test "$st" = "enable" -a ! -x /etc/init.d/S??$i; then
			start_stop $i enable
		elif test "$st" != "enable" -a -x /etc/init.d/S??$i; then
			start_stop $i disable
		fi
	done

elif test -n "$StartNow"; then
	start_stop $StartNow start

elif test -n "$StopNow"; then
	start_stop $StopNow stop

elif test -n "$Configure"; then
	if test -f $PWD/${Configure}.cgi; then
		gotopage /cgi-bin/${Configure}.cgi
	else
		write_header "$Configure setup"
		echo "<p>Write me</p>"
		back_button
		echo "</body></html>"
		exit 0
	fi
fi

#enddebug

back=$(echo $HTTP_REFERER | sed -n 's|.*/cgi-bin/||p')
gotopage /cgi-bin/$back
