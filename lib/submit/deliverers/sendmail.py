# -*- coding: utf-8 -*-
#
# This file is part of submit, a sendmail replacement or supplement for
# multi-user desktop systems.
#
# Copyright © 2008 Michael Schutte <michi@uiae.at>
#
# submit is available under the terms of the MIT/X license.  Please see the
# file COPYING for details.

from submit.deliverers import *
from submit.errors import *
from submit.i18n import *
import os
import shlex
import subprocess

__all__ = ["SendmailDeliverer"]

class SendmailDeliverer(AbstractDeliverer):
    """A deliverer submitting messages using a sendmail-compatible program."""

    def needs_authentication(self):
        """Sendmail-based delivery methods never ask for authentication."""
        return False

    def authenticate(self, auth):
        """No authentication needed; do nothing."""

    def abort(self):
        """Abort after a failed authentication procedure.  Authentication will
        never fail; still, do nothing."""

    def deliver(self, message, rcpts):
        """Pipe the message through sendmail."""
        program = self.config.get_method(str, self.method, "program",
                default_sendmail)
        if not program:
            raise DeliveryFailedError(n_(
                "Unable to find sendmail program."))
        sendmail = shlex.split(program)
        args = self.config.get_method(str, self.method, "arguments",
                "-oem -oi")
        if args: args = shlex.split(args)
        else: args = []

        cmd = sendmail + args + ["-f", message.efrom] + rcpts
        proc = subprocess.Popen(cmd,
                stdin = subprocess.PIPE, stderr = subprocess.PIPE)
        proc.stdin.write(message.get_body())
        proc.stdin.close()

        if proc.wait() != 0:
            details = proc.stderr.read().strip()
            if details:
                raise DeliveryFailedError(n_('"%(program)s" failed: %(details)s.'),
                        program=program, details=details)
            else:
                raise DeliveryFailedError(n_('"%(program)s" failed with unknown error.'),
                        program=program)

Deliverer = SendmailDeliverer

def default_sendmail():
    """Determine the path to the MTA sendmail implementation.  Take into
    account that `submit` itself might be called `sendmail`; in this case,
    `sendmail.notsubmit` is what we are looking for."""
    dirs = ("/usr/sbin", "/usr/lib")
    files = ("sendmail.notsubmit", "sendmail")
    for dir in dirs:
        for filename in files:
            filename = os.path.realpath(os.path.join(dir, filename))
            if os.path.basename(filename) == "submit":
                continue    # avoid loops
            elif os.access(filename, os.X_OK):
                return filename
    return None

# vim:tw=78:fo-=t:sw=4:sts=4:et:
