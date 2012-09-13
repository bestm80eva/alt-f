#############################################################
#
# mt-daapd
#
#############################################################
MT_DAAPD_VERSION = 0.2.4.2
MT_DAAPD_SOURCE = mt-daapd-$(MT_DAAPD_VERSION).tar.gz
MT_DAAPD_SITE = http://$(BR2_SOURCEFORGE_MIRROR).dl.sourceforge.net/project/mt-daapd/mt-daapd/$(MT_DAAPD_VERSION)
MT_DAAPD_AUTORECONF = NO
MT_DAAPD_INSTALL_STAGING = NO
MT_DAAPD_INSTALL_TARGET = YES
MT_DAAPD_LIBTOOL_PATCH = YES
MT_DAAPD_CONF_ENV = CFLAGS+=-DSETPGRP_VOID

MT_DAAPD_CONF_OPT = --disable-avahi --enable-oggvorbis
	
MT_DAAPD_DEPENDENCIES = uclibc gdbm libid3tag libvorbis

$(eval $(call AUTOTARGETS,package/multimedia,mt-daapd))

$(MT_DAAPD_HOOK_POST_EXTRACT):
	sed -i 's/^AC_FUNC_SETPGRP/dnl AC_FUNC_SETPGRP/' $(MT_DAAPD_DIR)/configure.in
	(cd $(MT_DAAPD_DIR); aclocal; autoconf; automake --add-missing)
	touch $@
