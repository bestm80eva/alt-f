#!/bin/sh

. common.sh
read_args
check_cookie

#debug

MIN_SIZE=20000 # minimum size of a partition or filesystem, in 512 bytes sectors (10MB)

# $1=error message
err() {
	busy_cursor_end
	cat<<-EOF
		<strong>failed:</strong></p>
		<pre>$1</pre>
		<input type="button" value="Back" onclick="window.location.assign(document.referrer)"></p>
		</body></html>
	EOF
	# restart hotplug
	echo /sbin/mdev > /proc/sys/kernel/hotplug
	exit 1
}

# load all disk
loadall() {
	for i in /dev/sd?; do
		dsk=$(basename $i)
		eject -r $dsk >& /dev/null
	done
}

# lower common size of all disks (in sectors)
minsize() {
	local i
	msz=9999999999 # 5.2TB

	for i in $disks; do
		sz=$(cat /sys/block/$(basename $i)/size)
		if test "$sz" -lt "$msz"; then
			msz=$sz
		fi
	done
	
	# subtract 1MB(2048 sectors), as fdisk, sfdisk, sgdisk, /sys/block/.../size report different sizes
	# subtract also 512MB(1048576 sectors) for swap size?
#	echo $(expr $msz - 2048 - 1048576)
	echo $(expr $msz - 2048)
}

# remove raid superblock to avoid auto rebuild on partially created arrays
# if by hazard the new partition table fits a previous one
cleanraid() {
	for i in $disks; do
		for j in $(sgdisk -p $i | awk '$6 == "DA00" || $6 == "FD00" {printf "%s ", $1}'); do
			mdadm --zero-superblock $i$j >& /dev/null
		done
	done
}

# 4k align: $1=pos, $2=nsect, $3=maxsect
align() {
	local nsect pos rem maxsect
	pos=$1
	nsect=$2
	maxsect=$3

	if test $(expr $pos + $nsect) -gt $maxsect; then
		nsect=$(expr $maxsect - $pos)
	fi

	rem=$(expr $nsect % 8)
	if test $rem -ne 0; then
		nsect=$(expr $nsect - $rem) # floor to previous 4k alignement
	fi
	echo $nsect
}

# clean traces of previous filesystems...
clean_traces() {
	for j in ${1}?; do
		if test -b $j; then
			dd if=/dev/zero of=$j count=1000 >& /dev/null
		fi
	done
}

# $1-disk (/dev/...), $2-std|raid, $3=equal, with equal sized partitions, $4-minsize
mbr_partition() {
	local i
	i=$1

	ptype="83"
	if test "$2" = "raid"; then
		ptype="da"
	fi

	echo "<p>MBR partitioning disk $(basename $i)..."

	clean_traces $i

if true; then
	eval $(sfdisk -l -uS $i | tr '*' ' ' | awk '
		/cylinders/ {printf "maxsect=%.0f;", $3 * $5 * $7}')
else
	maxsect=$(cat /sys/block/$(basename $i)/size)
fi

	if test "$maxsect" -gt 4294967296; then # 2^32, 2.2 TB
		maxsect=4294967296
	fi

	if test "$3" = "equal"; then
		commonsect=$4
	else
		commonsect=$maxsect
	fi

	pos=64 # 4k aligned
	nsect=1048576 # 512MB for swap
	nsect=$(align $pos $nsect $maxsect)

	pos2=$(expr $pos + $nsect)
	nsect2=$(expr $commonsect - $pos2)
	nsect2=$(align $pos2 $nsect2 $maxsect)

	par3=""
	if test "$maxsect" != "$commonsect"; then
		pos3=$(expr $pos2 + $nsect2)
		nsect3=$(expr $maxsect - $pos3)
		nsect3=$(align $pos3 $nsect3 $maxsect)
		if test "$nsect3" -gt "$MIN_SIZE"; then
			par3="$pos3,$nsect3,83"
		fi
	fi

	FMTFILE=$(mktemp -t sfdisk-XXXXXX)
	cat<<-EOF > $FMTFILE
		$pos,$nsect,S
		$pos2,$nsect2,$ptype
		$par3
	EOF

	# do it!
	sgdisk --zap-all $i >& /dev/null # start cleaning GPT data structures, if any
	res=$(sfdisk --force -uS $i < $FMTFILE 2>&1)
	if test $? != 0; then
		rm -f $FMTFILE
		err "$res"
	fi
	rm -f $FMTFILE

	sfdisk -R $i >& /dev/null
	sleep 3

	# somehow, in this scenario, mdev does not remove device, only creates them
	# yes, but mdev -s calls hot.sh, temporarily disable it 
	mv /etc/mdev.conf /etc/mdev.conf-
	rm -f ${i}[0-9]
	mdev -s
	mv /etc/mdev.conf- /etc/mdev.conf

	echo " done.</p>"
}

# $1-disk (/dev/...), $2-std|raid, $3=equal, with equal sized partitions, $4-minsize
gpt_partition() {
	local i commonsect
	i=$1

	echo "<p>GPT partitioning disk $(basename $i)..."

	clean_traces $i
	sgdisk --zap-all $i >& /dev/null
	res=$(sgdisk --set-alignment=8 --new=1:64:+512M --typecode=1:8200 $i)
	if test $? != 0; then
		err "Error creating swap: $res"
	fi

	firstend=$(sgdisk --set-alignment=8 --end-of-largest $i)
	if test "$2" = "raid"; then
		if test "$3" = "equal"; then
			commonsect="+$(expr $4 \* 512 / 1024 - 524288)K"
			cmd="--new=2:0:$commonsect --typecode=2:fd00"
		else
			cmd="--new=2:0:$firstend --typecode=2:fd00"
		fi
	else
		cmd="--new=2:0:$firstend --typecode=2:8300"
	fi

	res=$(sgdisk --set-alignment=8 $cmd $i)
	if test $? != 0; then
		err "Error creating first partition: $res"
	fi

	nextstart=$(sgdisk --set-alignment=8 --first-in-largest $i)
	nextend=$(sgdisk --set-alignment=8 --end-of-largest $i)
	nextleng=$(expr $nextend - $nextstart)
	if test	$nextstart -gt 64 -a $nextleng -gt $MIN_SIZE; then
		res=$(sgdisk --set-alignment=8 --new=3:$nextstart:$nextend --typecode=3:8300 $i)
		if test $? != 0; then
			err "Error creating second partition: $res"
		fi
	fi

	sleep 3

	# somehow, in this scenario, mdev does not remove device, only creates them
	# yes, but mdev -s calls hot.sh, temporarily disable it 
	mv /etc/mdev.conf /etc/mdev.conf-
	rm -f ${i}[0-9]
	mdev -s
	mv /etc/mdev.conf- /etc/mdev.conf

	echo " done.</p>"
}

# partition all disks
# $1=std|raid, $2=equal, with equal sized partitions
partition() {
	local i 

	commonsect=""
	if test "$2" = "equal"; then
		commonsect=$(minsize)
	fi

	for i in $disks; do
		if test "$(cat /sys/block/$(basename $i)/size)" -gt 4294967296; then # 2^32, 2.2 TB
			gpt_partition $i $1 $2 "$commonsect"
		else
			mbr_partition $i $1 $2 "$commonsect"
		fi
	done
	cleanraid
}

create_swap() {
	local i
	for i in $disks; do
		echo "<p>Creating and activating swap in disk $(basename $i)..."
		res="$(mkswap ${i}1 2>&1)"
		if test $? != 0; then
			err "$res"
		else
			res="$(swapon -p 1 ${i}1 2>&1)"
			if test $? != 0; then
				err "$res"
			else
				echo " done.</p>"
			fi
		fi
	done
}

# $1=dev
create_fs() {
		local dev sec sf
		if ! test -b $1; then return; fi
		dev=$(basename $1)
		raidopts=""
		if test "${dev:0:2}" = "md"; then
			sf=/sys/block/${dev}/size
			if test $wish_part = "raid0" -o $wish_part = "raid5"; then
				if test $wish_part = "raid0"; then
					nd=$ndisks
				else
					nd=2 # can start in degraded, but 3 (2 of data) has to be used
				fi
				blk=4096
				chunk=$(cat /sys/block/${dev}/md/chunk_size)
				stride=$((chunk / blk))
				stripew=$((stride * nd))
				raidopts="-b $blk -E stride=$stride,stripe-width=$stripew"
			fi
		else
			sf=/sys/block/${dev:0:3}/${dev}/size
		fi
		if test $(cat $sf) -lt $MIN_SIZE; then return; fi # don't create fs smaller than 10MB
		eval $(awk '{ printf "min=%.0f", ($1 * 512 / 1000000000 * 0.6 + 30) / 60}' $sf)
		echo "<p>Creating $wish_fs filesystem on $(basename $1). It will take roughly "
		wait_count_start "$min minute(s)"
		res="$(mke2fs -m 0 -T $wish_fs $raidopts ${1} 2>&1)"
		st=$?
		wait_count_stop
		if test $st != 0; then
			err "$res"
		else
			if test "$wish_fs" = "ext3"; then
				tune2fs -o journal_data_ordered ${1} >& /dev/null
			fi
			echo ". Done.</p>"
		fi
}

# $1=linear|raid0|raid1|raid5
create_raid() {
	curdev=$(mdadm --examine --scan | awk '{ print substr($2, match($2, "md"))}')
	for dev in $(seq 0 9); do
		if ! echo $curdev | grep -q md$dev; then MD=md$dev break; fi
	done

	pair1="missing"; pair2="missing"; spare=""

	if test $(ls /dev/sd? | wc -l) = $ndisks; then # all disks selected
		. /etc/bay
		if test -n "$left_dev"; then pair1=/dev/${left_dev}2; fi
		if test -n "$right_dev"; then pair2=/dev/${right_dev}2; fi
		usb=$(sed -n '/^usb/s/usb._dev=\(.*\)/\1/p' /etc/bay) # assume only one usb disk!
	else
		for i in $disks; do
			if test $pair1 = "missing"; then pair1=${i}2; continue; fi
			if test $pair2 = "missing"; then pair2=${i}2; continue; fi
		done
	fi

	opts="--chunk=512"; 
	case "$1" in
		linear|raid0)
			if test $ndisks = 3; then
				spare="/dev/${usb}2"
			fi
			;;
		raid1)  opts="$opts --bitmap=internal"
			if test $ndisks = 1; then
				pair2="missing"
				ndisks=2
			elif test $ndisks = 3; then
				spare="/dev/${usb}2"
				opts="$opts --spare-devices=1"
				ndisks=2
			fi
			;;
		raid5)  opts="$opts --bitmap=internal"
			if test $ndisks = 3; then
				spare="/dev/${usb}2"
			fi
			;;
	esac

	metad="0.9"
	for i in $pair1 $pair2 $spare; do
		if test $i = "missing"; then continue; fi
		j=$(basename $i)
		k=${j:0:3}
		if test "$(cat /sys/block/$k/$j/size)" -gt 4294967296; then # 2^32, 2.2 TB
			metad=1.2
			break
		fi
	done

	echo "<p>Creating $1 $MD..."
	res="$(mdadm --create /dev/$MD --run --level=$1 --metadata=$metad $opts \
		--raid-devices=$ndisks $pair1 $pair2 $spare 2>&1)"
	if test $? != 0; then
		err "Error $?: $res"
	else
		echo " done.</p>"
	fi
}

standard() {
	local i

	partition
	create_swap
	for i in $disks; do
		create_fs ${i}2
	done
}

jbd() {
	partition raid
	create_swap
	create_raid linear
	create_fs /dev/$MD
}

raid0() {
	local i
	partition raid equal
	create_swap
	create_raid raid0
	create_fs /dev/$MD
        for i in $disks; do                                                            
        	create_fs ${i}3                                                        
	done
}

raid1() {
	local i
	partition raid equal
	create_swap
	create_raid raid1
	create_fs /dev/$MD
	for i in $disks; do
		create_fs ${i}3
	done
}

raid5() {
	local i
	partition raid equal
	create_swap
	create_raid raid5
	create_fs /dev/$MD
	for i in $disks; do
		create_fs ${i}3
	done
}

if test "$wish_fs" != "ext2" -a "$wish_fs" != "ext3" -a \
		"$wish_fs" != "ext4";then
	msg "Unknown filesystem type $wish_fs"
fi

if test "$wish_part" != "notouch" -a "$wish_part" != "standard" -a \
		"$wish_part" != "jbd" -a "$wish_part" != "raid0" -a \
		"$wish_part" != "raid1" -a "$wish_part" != "raid5"; then
	msg "Unknown disk layout type $wish_part"
fi

if test "$advise" != "Abracadabra"; then
	msg "Unknown operation"
fi

#has_disks
ndisks=0
for i in $(seq 1 $num_disks); do
	dsk=$(eval echo \$disk_$i)
	if test -n "$dsk"; then
		disks="$disks /dev/$dsk"
		ndisks=$((ndisks+1))
	fi
done
#echo "$ndisks $disks"

if test "$ndisks" = "0" -o "$wish_part" = "notouch"; then
	gotopage /cgi-bin/diskmaint.cgi
fi

#exit 0

html_header
echo "<center><h2>Disk Wizard</h2></center>"
busy_cursor_start

echo "<p>Stopping all services and disks..."
if ! eject -a; then
	err ""
fi

# stop hotplug
echo > /proc/sys/kernel/hotplug

echo " done.</p>"

case $wish_part in
	notouch) ;;
	standard) standard ;;
	jbd) jbd ;;
	raid0) raid0 ;;
	raid1) raid1 ;;
	raid5) raid5 ;;
esac

echo "<p>Reloading all disks and restarting all boot-enabled services..."
loadall
rcall start >& /dev/null

# restart hotplug
echo /sbin/mdev > /proc/sys/kernel/hotplug

#enddebug

busy_cursor_end

cat<<-EOF
	</pre><p><strong>Success!</strong></p>
	<script type="text/javascript">
		url = document.referrer
		url = url.substr(0,url.lastIndexOf("/")) + "/diskmaint.cgi"
		setTimeout("window.location.assign(url)", 3000);
	</script></body></html>
EOF
