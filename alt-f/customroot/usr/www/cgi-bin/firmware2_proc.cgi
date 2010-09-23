#!/bin/sh

. common.sh
read_args

kernel_file="/tmp/kernel"
initramfs_file="/tmp/initramfs"
defaults_file="/tmp/defaults"

if test $flash = "Abort"; then
	rm $kernel_file $initramfs_file $defaults_file > /dev/null 2>&1
	gotopage /cgi-bin/firmware.cgi
fi

html_header
	
if test $flash = "FlashIt"; then
	if ! test -f $kernel_file -a -f $initramfs_file; then
		rm $kernel_file $initramfs_file $defaults_file > /dev/null 2>&1
		cat<<-EOF
			<br>
			<form action="/cgi-bin/firmware.cgi" method="post">
			Kernel and/or ramdisk file missing <input type="submit" value="Retry">
			</form></body></html>
		EOF
		exit 0
	fi

	if test "$flash_defaults" = "yes" -a ! -s $defaults_file; then
		rm $kernel_file $initramfs_file $defaults_file > /dev/null 2>&1
		cat<<-EOF
			<br>
			<form action="/cgi-bin/firmware.cgi" method="post">
			defaults file missing or empty <input type="submit" value="Retry">
			</form></body></html>
		EOF
		exit 0
	fi

	rcall stop >& /dev/null

	echo timer > "/sys/class/leds/power:blue/trigger"
	echo 50 > "/sys/class/leds/power:blue/delay_off" 
	echo 50 > "/sys/class/leds/power:blue/delay_on"

	echo "<p>Flashing the kernel, it takes about 20 seconds "

	cat $kernel_file > /dev/mtdblock2 &
	while test "$(jobs)" != ""; do jobs >/dev/null; echo .; sleep 1; done
	echo "done.</p>"

# FIXME compute md5sum to make sure flahing was OK.

	echo "<p>Flashing the ramdisk, it takes about 90 seconds "
	cat $initramfs_file > /dev/mtdblock3 &
	while test "$(jobs)" != ""; do jobs >/dev/null; echo .; sleep 1; done
	echo "done.</p>"

# FIXME compute md5sum to make sure flahing was OK.

	if test "$flash_defaults" = "yes"; then
		echo "<p>Flashing defaults, it takes about 10 seconds..."

		tar -C /tmp -xzf $defaults_file
		mkdir /tmp/mtd
		mount /dev/mtdblock0 /tmp/mtd
		rm -f /tmp/mtd/*
		cp -f /tmp/default/* /tmp/mtd/
		umount /tmp/mtd

		mount /dev/mtdblock1 /tmp/mtd
		rm -f /tmp/mtd/*
		cp -f /tmp/default/* /tmp/mtd/
		umount /tmp/mtd

		rm -rf /tmp/default
		rmdir /tmp/mtd
		 
		echo " done.</p>"
	fi

# FIXME handle mtd2. vendor bootlog: MTDC: Backup files from MTD1 to MTD2.

rm $kernel_file $initramfs_file $defaults_file > /dev/null 2>&1

echo none > "/sys/class/leds/power:blue/trigger"

cat<<-EOF
	<center>
	<form action="/cgi-bin/sys_utils_proc.cgi" method="post">
	<input type=submit name=action value=Reboot onClick="return confirm('The box will reboot now.\nWait 30 seconds to connect again.\n\nProceed?')">
	</body></html>
EOF
	exit 0
fi

