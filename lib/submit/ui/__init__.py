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

__all__ = ["AbstractInterface", "InterfaceError"]

class InterfaceError(Exception):
    """A UI-related error has occurred."""

class AbstractInterface:
    """Superclass for user interface implementations. User interfaces to
    submit present error messages and ask for passwords.  This abstraction
    makes it possible to offer console-based as well as graphical
    authentication dialogs, etc."""

    def __init__(self):
        """Create the interface.  Call the `check` method to see whether it
        can be used.  If it cannot, raise an `InterfaceError`."""
        if not self.check():
            raise InterfaceError, "UI not available"

    def check(self):
        """Determine if this interface is supported under the current
        cirumstances.  This method must be overrided in subclasses to check
        whether required modules are available, whether standard input is a
        terminal, whether $DISPLAY is set, etc."""
        raise NotImplementedError, "abstract check() called"

    def prepare(self):
        """Prepare the interface: Do things like showing a banner or creating
        windows."""
        raise NotImplementedError, "abstract prepare() called"

    def show_error(self, error):
        """Display a `UserError`.  It is not yet internationalized; most
        interfaces will want to call `submit.i18n._` to do so."""
        raise NotImplementedError, "abstract show_error() called"

    def ask_password(self, method, key, message, first):
        """A delivery `method` has asked for the password specified by `key`.
        Ask for it, showing `message` (which should usually go through
        `submit.i18n._` first).  `first` is false if there have been earlier
        attempts to obtain the correct password, but they have failed."""
        raise NotImplementedError, "abstract ask_password() called"

    def ask_password_title(self, method):
        """Get a translated string usable, for example, for dialog title bars,
        which takes into account the special nature of the `local` and
        `remote` methods."""
        if method == "local":
            return _("Supply credentials for local mail delivery")
        elif method == "remote":
            return _("Supply credentials for mail delivery to remote hosts")
        else:
            return _('Supply credentials for mail delivery via "%s"') % method

    def stores_passwords(self):
        """Can this interface store passwords itself?  This should return true
        if the user interface uses some sort of keyring manager."""
        raise NotImplementedError, "abstract stores_passwords() called"

# vim:tw=78:fo-=t:sw=4:sts=4:et:
