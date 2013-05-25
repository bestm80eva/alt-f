#!/bin/sh

. common.sh
check_cookie
read_args

CONFF=/etc/msmtprc
CONFM=/etc/misc.conf
CONFA=/etc/msmtprc.alias

if test -z "$tls"; then tls=off; fi
#if test -z "$auth"; then auth=on; fi

if test -z "$to"; then
	msg "\"To\" entry must be filled"
fi

if test -z "$from"; then
	msg "\"From\" entry must be filled"
fi

if test -z "$host"; then
	msg "Server Name must be filled"
fi

if test "$auth" != "off"; then
	if test -z "$user" -o -z "$password"; then
		msg "Username and Password must be filled"
	else
		password=$(checkpass "$password")
		if test $? != 0; then
			msg "$password"
		fi
	fi
fi

user=$(httpd -d "$user")
to=$(httpd -d "$to")
from=$(httpd -d "$from")

#debug

echo "
tls_trust_file	/etc/ssl/ca-bundle.crt
syslog		on
host	$host
tls		$tls
auth	$auth
from	$from
aliases	$CONFA" > $CONFF

sed -i '/^MAILTO=/d' $CONFM
echo "MAILTO=$to" >> $CONFM

sed -i '/^default/d' $CONFA >&/dev/null
echo -e "default\t$to" >> $CONFA

if test -n "$port"; then echo -e "port\t$port" >> $CONFF; fi
if test -n "$user"; then echo -e "user\t$user" >> $CONFF; fi
if test -n "$password"; then echo -e "password\t$password" >> $CONFF; fi

chmod 600 $CONFF

if test "$submit" = "Test"; then
	msmtp --read-recipients >& /dev/null <<-EOF
		To: $to
		From: $from
		Subject: DNS-323 ALT-F mail test
		
		This is a test message
	EOF
	if test $? = 0; then
		msg "Mail sent."
	else
		msg "Sent mail failed: $(logread | grep msmtp | tail -1)"
	fi
fi

#enddebug
gotopage /cgi-bin/mail.cgi

