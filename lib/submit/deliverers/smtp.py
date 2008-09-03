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
from submit.deliverers import *
from submit.errors import *
from submit.message import default_mailname
import smtplib
import socket
import re
from OpenSSL import crypto, SSL

__all__ = ["SMTPDeliverer"]

class SMTP(smtplib.SMTP):
    """An SMTP client implementation supporting OpenSSL-based STARTTLS
    facilities."""

    def starttls(self, context):
        """Start a TLS session.  The SSL parameters are taken from the
        `context` parameter.

        Don’t forget to re-EHLO afterwards, some servers will refuse to
        continue if this step is missing."""
        (resp, reply) = self.docmd("STARTTLS")
        if resp == 220:
            self.sock = SSL.Connection(context, self.sock)
            self.file = smtplib.SSLFakeFile(self.sock)
            self.sock.set_connect_state()
            self.sock.do_handshake()
            # and suddenly, the server is a stranger again (RFC 3207, 4.2)
            self.helo_resp = None
            self.ehlo_resp = None
            self.esmtp_features = {}
            self.does_esmtp = 0
        return (resp, reply)

class SMTPDeliverer(AbstractDeliverer):
    """A deliverer submitting messages to SMTP servers."""

    def needs_authentication(self):
        """SMTP deliverers only need manual authentication when SASL is used
        and no password is provided in the configuration file.  There is the
        second case of a PEM private key with a passphrase, but this is
        considered unlikely."""
        username = self.config.get_method(str, self.method, "username")
        password = self.config.get_method(str, self.method, "password")
        return username and not password

    def authenticate(self, auth):
        """Open a connection to an SMTP server."""
        c = self.config

        self.host = host = c.get_method(str, self.method, "host")
        port = c.get_method(int, self.method, "port", smtplib.SMTP_PORT)
        try:
            self.conn = SMTP(host, port)
        except:
            raise AuthenticationFailedError(
                    n_("Unable to open connection to %(host)s."), host=host)

        try:
            self.ehlo()
            starttls = c.get_method(bool, self.method, "starttls", False)
            if starttls:
                self.tls_setup(auth)
            self.sasl_auth(auth)
        except (socket.error, smtplib.SMTPException), e:
            raise AuthenticationFailedError(
                    n_("Error while talking to %(host)s: %(details)s"),
                    host=host, details=str(e))

    def ehlo(self):
        """Say hello to the SMTP server."""
        self.conn.ehlo(self.config.get_method(str, self.method,
            "ehlo", default_mailname))

    def init_ssl_context(self, auth, method):
        """Create an SSL context for the given method
        (`openssl.SSL.*_METHOD`), using the settings from the configuration
        file."""
        c = self.config

        ca = c.get_method(str, self.method, "ca")
        fingerprint = c.get_method(str, self.method, "fingerprint")
        key = c.get_method(str, self.method, "key")
        cert = c.get_method(str, self.method, "cert")

        cx = SSL.Context(method)

        if ca:
            try: cx.load_verify_locations(c.path(ca))
            except (SSL.Error, IOError), e: raise AuthenticationFailedError(
                    n_("Unable to read CA file: %s."), str(e))

            cx.set_verify(SSL.VERIFY_PEER,
                    lambda conn, cert, errnum, depth, ok: ok)

        if fingerprint:
            fingerprint = re.sub(r"[^0-9a-fA-F]", "", fingerprint).lower()
            if len(fingerprint) != 40:
                raise AuthenticationFailedError(
                        n_("Please specify an SHA-1 fingerprint."))

            def verify_fingerprint(conn, cert, errnum, depth, ok):
                if depth == 0:
                    peer = cert.digest("sha1").replace(":", "").lower()
                    return (peer == fingerprint) and ok
                else:
                    return ok

            cx.set_verify(SSL.VERIFY_PEER, verify_fingerprint)

        if key:
            cx.use_privatekey(self.load_private_key(auth, key))

            if not cert:
                raise AuthenticationFailedError(
                        n_("You must specify a certificate if you want to "
                            "use a private key."))

            try: cx.use_certificate_file(c.path(cert))
            except (SSL.Error, IOError), e: raise AuthenticationFailedError(
                    n_("Unable to read TLS certificate: %(details)s."),
                    details=str(e))

        return cx

    def tls_setup(self, auth):
        """Start transport layer security on the connection to the SMTP server."""
        cx = self.init_ssl_context(auth, SSL.TLSv1_METHOD)
        try:
            self.conn.starttls(cx)
        except (SSL.Error, crypto.Error), e:
            raise AuthenticationFailedError(
                    n_("Error while trying to establish an encrypted "
                    "connection to %(host)s: %(details)s."),
                    host=self.host, details=e.message[0][2])
        self.ehlo()

    def load_private_key(self, auth, key):
        """Load a private key file.  If necessary, ask for a passphrase until
        the correct one was specified by the user."""
        try:
            source = self.config.file(key).read()
        except IOError, e:
            raise AuthenticationFailedError(
                    n_("Unable to read private key file: %(details)s."),
                    details=str(e))

        first = True
        pph = ""
        errmsg = None
        # try to read passwords until the user provides the right one or
        # cancels (get_password will raise an exception then)
        while True:
            try:
                pkey = crypto.load_privatekey(crypto.FILETYPE_PEM, source, pph)
            except crypto.Error, e:
                if e.message[0][2] not in ("bad password read", "bad decrypt"):
                    errmsg = str(e)
                    break
                if first:
                    first = False
                else:
                    auth.remove_password("key_passphrase")
                pph = auth.get_password(self.config, "key_passphrase",
                        n_("Please enter the passphrase to your private key: "))
            except (SSL.Error, IOError), e:
                errmsg = str(e)
                break
            else:
                return pkey

        raise AuthenticationFailedError(
                n_("Unable to read TLS private key: %(details)s."),
                details=errmsg)

    def sasl_auth(self, auth):
        """Authenticate with user name and password."""
        c = self.config

        username = c.get_method(str, self.method, "username")
        if username is None: return

        # try to authenticate with the SMTP server until the user provides the
        # right password or cancels
        while True:
            password = auth.get_password(self.config, "password",
                    n_("Please enter your SMTP password: "))
            try:
                self.conn.login(username, password)
                break
            except smtplib.SMTPAuthenticationError:
                auth.remove_password("password")
                continue
            except smtplib.SMTPException:
                raise AuthenticationFailedError(
                        n_("Could not find a suitable SMTP authentication mechanism."))

    def abort(self):
        """Close the connection after the authentication procedure."""
        try:
            self.close()
        except:
            pass    # ignore it, we are aborting anyway

    def deliver(self, message, rcpts):
        """Transmit the message."""

        def err(result):
            if 200 <= result[0] < 300: return
            raise DeliveryFailedError(
                    n_("SMTP transmission failed with error code %(code)d: %(details)s."),
                    code=result[0], details=result[1])

        try:
            err(self.conn.mail(message.efrom))
            for rcpt in rcpts:
                err(self.conn.rcpt(rcpt))
            err(self.conn.data(message.get_body()))
            self.close()

        except (socket.error, smtplib.SMTPException), e:
            raise DeliveryFailedError(
                    n_("Error while talking to %(host)s: %(details)s"),
                    host=self.host, details=str(e))

    def close(self):
        """Close the connection."""
        self.conn.quit()

Deliverer = SMTPDeliverer

# vim:tw=78:fo-=t:sw=4:sts=4:et:
