# -*- coding: utf-8 -*-
#
# This file is part of submit, a sendmail replacement or supplement for
# multi-user desktop systems.
#
# Copyright © 2008 Michael Schutte <michi@uiae.at>
#
# submit is available under the terms of the MIT/X license.  Please see the
# file COPYING for details.

from submit.i18n import *
from submit.ui import *
import sys
from getpass import getpass

__all__ = ["TTYInterface"]

class TTYInterface(AbstractInterface):
    """A very simple terminal-based interface."""

    def check(self):
        """See whether stdin is connected to a terminal.  Otherwise, we don’t
        want to use it to ask for passwords, obviously."""
        return sys.stdin.isatty()

    def prepare(self):
        """No-op."""

    def show_error(self, error):
        """Display an error message."""
        print >>sys.stderr, gettext(error.message) % error.params

    def ask_password(self, method, key, message, first):
        """Query for a password."""
        print >>sys.stderr, "*** " + self.ask_password_title(method)
        try:
            return getpass(gettext(message))
        except EOFError:
            return None     # cancel delivery

    def stores_passwords(self):
        """This UI cannot store passwords itself."""
        return False

Interface = TTYInterface

# vim:tw=78:fo-=t:sw=4:sts=4:et:
