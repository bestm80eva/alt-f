#!/bin/sh

. common.sh
check_cookie
read_args

#debug

CONFF=/etc/minidlna.conf

if test -n "$enable_tivo"; then
	enable_tivo=yes
else
	enable_tivo=no
fi

if test -n "$strict_dlna"; then
	strict_dlna=yes
else
	strict_dlna=no
fi

if test -n "$force_rescan"; then
	force_rescan=yes
else
	force_rescan=no
fi

sed -i 's/^enable_tivo=.*$/enable_tivo='$enable_tivo'/' $CONFF
sed -i 's/^strict_dlna=.*$/strict_dlna='$strict_dlna'/' $CONFF
sed -i 's/^#force_rescan=.*$/#force_rescan='$force_rescan'/' $CONFF

# save old, in case of errors
sed -i 's/^media_dir=.*$/#!#&/' $CONFF

for i in $(seq 1 $cnt); do
	d="$(eval echo \$sdir_$i)"
	if test -z "$d"; then continue; fi
	if test -n "$d"; then
		s=$(httpd -d $d)
		if ! test -d "$s"; then
			sed -i -e '/^!#!media_dir=.*$/d' \
				-e 's/^#!#\(media_dir=.*$\)/\1/' $CONFF
			msg "A directory does not exist."
		fi
		echo "!#!media_dir=$s" >> $CONFF
	fi
done

# sucess, delete old, update new
sed -i -e '/^#!#media_dir=.*$/d' -e 's/^!#!\(media_dir=.*$\)/\1/' $CONFF

if rcminidlna status >& /dev/null; then
	rcminidlna restart >& /dev/null
fi

#enddebug
gotopage /cgi-bin/user_services.cgi

