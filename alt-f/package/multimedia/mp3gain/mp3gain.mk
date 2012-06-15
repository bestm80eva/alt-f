################################################################################
#
# mp3gain
#
################################################################################

MP3GAIN_VERSION = 1.5.2
MP3GAIN_VERSION2 = 1_5_2_r2
#MP3GAIN_DIR = $(MP3GAIN_VERSION2)
MP3GAIN_SOURCE = mp3gain-$(MP3GAIN_VERSION2)-src.zip
MP3GAIN_SITE = http://$(BR2_SOURCEFORGE_MIRROR).dl.sourceforge.net/project/mp3gain/mp3gain/$(MP3GAIN_VERSION)
MP3GAIN_AUTORECONF = NO
MP3GAIN_INSTALL_TARGET = YES
MP3GAIN_INSTALL_STAGING = NO

$(eval $(call AUTOTARGETS,package/multimedia,mp3gain))

$(MP3GAIN_TARGET_EXTRACT):
	unzip $(DL_DIR)/$(MP3GAIN_SOURCE) -d $(MP3GAIN_DIR)
	touch $@

$(MP3GAIN_TARGET_CONFIGURE):
	touch $@

$(MP3GAIN_TARGET_BUILD):
	$(MAKE) CC=$(TARGET_CC) CFLAGS="$(TARGET_CFLAGS)" -C $(MP3GAIN_DIR)
	touch $@

$(MP3GAIN_TARGET_INSTALL_TARGET):
	$(MAKE) CC=$(TARGET_CC) CFLAGS="$(TARGET_CFLAGS)" INSTALL_PATH="$(TARGET_DIR)/usr/bin" -C $(MP3GAIN_DIR) install
	touch $@

#$(MP3GAIN_HOOK_POST_INSTALL):
#	touch $@