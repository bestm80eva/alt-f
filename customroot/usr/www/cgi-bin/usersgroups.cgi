#!/bin/sh

. common.sh
check_cookie
write_header "Users and Groups Setup"

BRD=0

cat <<EOF
	<script type="text/javascript">
	var users = new Array();
	var groups = new Array();
	var groupsInUser = new Array();
	var usersInGroup = new Array();
	function update_users() {
		document.frm.uname.value = document.frm.users.value;
		document.frm.nick.value = users[document.frm.users.selectedIndex];
		document.frm.groupsInUser.value = groupsInUser[document.frm.users.selectedIndex]
	}
	function update_groups() {
		document.frm.gname.value = groups[document.frm.groups.selectedIndex];
		document.frm.usersInGroup.value = usersInGroup[document.frm.groups.selectedIndex]
	}
	function check_group() {
		if (document.frm.gname.value == "") {
			alert("You must fill in the group name or select one group first.")
			return false
		}
		return true
	}
	function check_user() {
		if (document.frm.uname.value == "") {
			alert("You must fill in the user name or select one user first.")
			return false
		}
		return true
	}
	function check_usergroup() {
		if (check_user() && check_group())
			return true
		else
			return false
	}
	</script>
	<form name=frm action=/cgi-bin/usersgroups_proc.cgi method="post">
	<table border=$BRD><tr><td>
	
	<fieldset><legend><strong>Users</strong></legend>
	<table border=$BRD>
EOF


IFS=":" # WARNING: for all the script
#account:password:UID:GID:GECOS:directory:shell
cnt=0
echo "<tr><td colspan=2><SELECT MULTIPLE style='width:40ex' SIZE=8 NAME=users onChange=update_users()>"
while read user upass uid ugid uname dir shell;do
	if test "${user:0:1}" = "#" -o -z "$user" -o -z "$uid" -o -z "$uname"; then continue; fi
	if test $shell = "/bin/false"; then continue; fi
	if test $uid -lt 100; then continue; fi
	echo "<OPTION>$uname</OPTION>"
	echo "<script type=text/javascript>users[$cnt]=\"$user\"; groupsInUser[$cnt]=\"$(id -Gn $user)\";</script>"
	cnt=$((cnt+1))
done < /etc/passwd
echo "</SELECT></td></tr>"
num_users=$cnt

cat<<-EOF
	<tr><td>User name</td><td><input type=text size=12 name=uname></td></tr>
<!--	<tr><td>Nick name<td><input type=text size=12 name=nick></td></tr> -->
	<input type=hidden size=12 name=nick>
	<tr><td>Groups this user belongs to:</td>
		<td><textarea cols=12 name=groupsInUser READONLY></textarea></td></tr>
	<tr><td><input type=submit name=new_user value=NewUser>
		<input type=submit name=change_pass value=ChangePass onclick="return check_user()">
		<td><input type=submit name=del_user value=DelUser onclick="return check_user()"></td>
	</tr></table></fieldset>
	
	</td><td>
	
	<fieldset><legend><strong>Groups</strong></legend>
	<table border=$BRD>
EOF

#group_name:passwd:GID:user_list
cnt=0
echo "<td colspan=2><SELECT MULTIPLE style='width:40ex' SIZE=8 NAME=groups onChange=update_groups()>"
while read group gpass ggid userl;do
	if test "${group:0:1}" = "#" -o "$gpass" = "!"; then continue; fi
	if test $ggid -lt 100; then continue; fi
	echo "<OPTION>$group</OPTION>"
	# primary group
	uu=$(awk -F: '{if ($4 == '$ggid') printf "%s, ", $5}' /etc/passwd)
	# suplementary groups
	if test -n "$userl"; then 
		for i in $(echo $userl | tr ',' ':'); do # IFS is a ":"
			uu="$uu, $(awk -F: '/'$i'/{print $5}' /etc/passwd)"
		done
	fi
	echo "<script type=text/javascript>groups[$cnt]=\"$group\";usersInGroup[$cnt]=\"$uu\"</script>"
	cnt=$((cnt+1))
done < /etc/group
echo "</SELECT></td></tr>"
num_groups=$cnt

cat <<-EOF
	<tr><td>Group name</td><td><input type=text size=12 name=gname></td></tr>
<!--	<tr><td colspam=2><br></td></tr> -->
	<tr><td>Users belonging to this group:</td>
		<td><textarea cols=12 name=usersInGroup READONLY></textarea></td></tr>
	<tr><td><input type=submit name=new_group value=NewGroup onclick="return check_group()"></td>
	    <td><input type=submit name=del_group value=DelGroup onclick="return check_group()"></td></tr>
	</table></fieldset>
	
	</td></tr></table><br>
	
	<fieldset><legend><strong>Users and Groups</strong></legend><table border=$BRD>
		<tr><td>Add selected user to selected group</td>
			<td><input type=submit name=addToGroup value=AddToGroup onclick="return check_usergroup()"></td></tr>
		<tr><td>Remove selected user from selected group</td>
			<td><input type=submit name=delFromGroup value=DelFromGroup onclick="return check_usergroup()"></td></tr>
	</table></fieldset>
EOF

echo "</form></body></html>"
