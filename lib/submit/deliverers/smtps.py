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
from submit.deliverers.smtp import *
from submit.errors import *
import smtplib
import socket
from OpenSSL import crypto, SSL

__all__ = ["SMTPSDeliverer"]

SMTPS_PORT = 465

class SMTPSDeliverer(SMTPDeliverer):
    """A deliverer submitting messages to SMTPS servers."""

    def authenticate(self, auth):
        """Open a connection to an SMTPS server."""
        c = self.config

        self.host = host = c.get_method(str, self.method, "host")
        port = c.get_method(int, self.method, "port", SMTPS_PORT)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            ssl = SSL.Connection(self.init_ssl_context(auth, SSL.SSLv23_METHOD),
                    sock)
            ssl.connect((host, port))
            conn = self.conn = smtplib.SMTP()
            conn.sock = ssl
            conn.file = smtplib.SSLFakeFile(ssl)
        except (SSL.Error, crypto.Error), e:
            raise AuthenticationFailedError(
                    n_("Error while trying to establish an encrypted "
                    "connection to %s: %s."), (self.host, e.message[0][2]))
        except (socket.error, IOError, smtplib.SMTPException), e:
            raise AuthenticationFailedError(
                    n_("Unable to open connection to %s."), host)

        try:
            self.ehlo()
            self.sasl_auth(auth)
        except (socket.error, smtplib.SMTPException), e:
            raise AuthenticationFailedError(
                    n_("Error while talking to %s: %s"),
                    (host, str(e)))

Deliverer = SMTPSDeliverer

# vim:tw=78:fo-=t:sw=4:sts=4:et:
