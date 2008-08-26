# -*- coding: utf-8 -*-
#
# This file is part of submit, a sendmail replacement or supplement for
# multi-user desktop systems.
#
# Copyright © 2008 Michael Schutte <michi@uiae.at>
#
# submit is available under the terms of the MIT/X license.  Please see the
# file COPYING for details.

from submit.errors import *
from submit.i18n import *
from submit.ui import *
from submit.ui.gtk_ui import *
import os

try:
    import gnomekeyring
except ImportError:
    gnomekeyring = None

__all__ = ["GNOMEInterface"]

class GNOMEInterface(GTKInterface):
    """A gnome-keyring based interface.  For a UI that looks “native” under
    GNOME, but does not use the keyring API, see `submit.ui.gtk_ui`."""

    def check(self):
        """Determine whether gnome-keyring is available and usable."""
        if not GTKInterface.check(self): return False
        return (gnomekeyring is not None) and (gnomekeyring.is_available())

    def prepare(self):
        """Open the default keyring."""
        self.keyring = gnomekeyring.get_default_keyring_sync()

    def ask_password(self, method, key, message, first):
        """Query for a password."""
        display_name = "submit password %s.%s" % (method, key)
        attrs = dict(submit=1, method=method, key=key)
        try:
            # first try: perhaps the correct password is in the keyring
            if first:
                try:
                    items = gnomekeyring.find_items_sync(
                            gnomekeyring.ITEM_GENERIC_SECRET, attrs)
                    return items[0].secret
                except gnomekeyring.NoMatchError:
                    pass

            # no, it isn’t; show a dialog to get the password
            password, store = self.password_dialog(
                    method, key, message, first, True)
            if password is None: return None

            if store:
                gnomekeyring.item_create_sync(
                        self.keyring, gnomekeyring.ITEM_GENERIC_SECRET,
                        display_name, attrs, password, True)

            return password

        except gnomekeyring.DeniedError:
            raise AuthenticationFailedError(
                    n_("Unable to access GNOME keyring."))

    def stores_passwords(self):
        """This UI cannot store passwords itself."""
        return True

Interface = GNOMEInterface

# vim:tw=78:fo-=t:sw=4:sts=4:et:
