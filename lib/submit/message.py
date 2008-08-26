# -*- coding: utf-8 -*-
#
# This file is part of submit, a sendmail replacement or supplement for
# multi-user desktop systems.
#
# Copyright © 2008 Michael Schutte <michi@uiae.at>
#
# submit is available under the terms of the MIT/X license.  Please see the
# file COPYING for details.

import os
import pwd
import socket
import email
import email.utils
import email.parser

__all__ = ["Message"]

class Message:
    """A message handled by submit, composed of a body, some recipient
    addresses and an envelope sender address."""

    def __init__(self, config, body, rcpts, parse_rcpts = False, efrom = None):
        """Create a new message to the given recipients containing the text
        given in `body`.  If no envelope sender address is passed in `efrom`,
        it is guessed from the message body.  If `parse_rcpts` is true, the
        message body is parsed for additional recipients."""
        self.rcpts = set()
        for rcpt in rcpts:
            name, addr = email.utils.parseaddr(rcpt)
            if addr:
                self.rcpts.add(addr)

        parser = email.parser.Parser()
        self.message = parser.parsestr(self.received() + body, True)

        if efrom is None:
            if not self.message.has_key("from"):
                default_from = config.get_general(str, "default_from")
                if default_from:
                    self.message["From"] = default_from
            self.efrom = self.guess_envelope_from()
        else:
            self.efrom = efrom

        if not self.message.has_key("from"):
            self.message["From"] = self.efrom

        if parse_rcpts:
            self.add_recipient_addresses()

        self.fix_headers()

    def received(self):
        """Return a Received: header."""
        return "Received: by %s (submit); %s\n" % (socket.gethostname(),
                email.utils.formatdate())

    def guess_envelope_from(self):
        """Try to guess the envelope sender address to be used for mail
        submission.  First check the message body for a From: line.  If there
        is none, use the name of the submitting user and append an at sign and
        the contents of /etc/mailname (or the output of hostname, if this file
        is missing too)."""
        if self.message.has_key("from"):
            return email.utils.parseaddr(self.message["from"])[1]

        username = pwd.getpwuid(os.getuid())[0]
        mailname = default_mailname()
        return "%s@%s" % (username, mailname)

    def add_recipient_addresses(self):
        """Add the addresses from the To:, Cc: and Bcc: fields to the set of
        recipients."""
        for header in ("to", "cc", "bcc"):
            rcpts = email.utils.getaddresses(self.message.get_all(header, []))
            for name, addr in rcpts:
                if addr: self.rcpts.add(addr)

    def fix_headers(self):
        """Remove all Bcc: headers, add Date: and Message-ID: headers if they
        are missing."""
        del self.message["bcc"]
        if not self.message.has_key("message-id"):
            self.message["Message-ID"] = email.utils.make_msgid()
        if not self.message.has_key("date"):
            self.message["Date"] = email.utils.formatdate()

    def get_delivery_methods(self, config):
        """Return (name, addresses) tuples of the config sections that apply
        for sending this message."""
        methods = [method for method in config.get_methods()
                if method not in ("local", "remote")]
        methods.insert(0, "local")
        methods.append("remote")

        dummy, fromaddr = email.utils.parseaddr(self.message["from"])
        # (domain, method) mappings
        dom_meth = []
        for method in methods:
            # skip the method if its “from” option is set and doesn’t match
            # the From: header of this message
            onlyfroms = config.get_method(str, method, "from")
            if onlyfroms:
                onlyfroms = onlyfroms.split(",")
                for onlyfrom in onlyfroms:
                    onlyfrom = onlyfrom.strip()
                    if onlyfrom.startswith("@"):
                        if fromaddr.endswith(onlyfrom):
                            break
                    else:
                        if fromaddr == onlyfrom:
                            break
                else:
                    continue

            if method == "local":
                domains = self.get_local_domains(config)
            else:
                domains = config.get_method(str, method, "domains")
                if not domains: domains = [None]
                else: domains = self.parse_domains(domains)

            for domain in domains:
                dom_meth.append((domain, method))

        # (method, recipients) mappings
        # initialize as {meth1: [], meth2: [], …}
        meth_rcpt = dict([(method, []) for method in methods])
        for rcpt in self.rcpts:
            # no @ sign: local address
            if rcpt.find("@") == -1:
                meth_rcpt["local"].append(rcpt)
                continue
            # else, look for an appropriate mapping
            for domain, method in dom_meth:
                if domain is None or rcpt.endswith("@" + domain):
                    meth_rcpt[method].append(rcpt)
                    break
            # if there is none, go with remote
            else:
                meth_rcpt["remote"].append(rcpt)

        result = []
        for method in methods:
            if len(meth_rcpt[method]) > 0:
                result.append((method, meth_rcpt[method]))
        result.reverse()    # local delivery to the end, most likely to succeed

        return result

    def create_deliverers(self, config):
        """Like `get_delivery_methods`, but return (deliverer, addresses)
        tuples instead."""
        result = []
        for method, rcpts in self.get_delivery_methods(config):
            result.append((config.create_deliverer(method), rcpts))
        return result

    def get_local_domains(self, config):
        """Get the list of domains considered local (which usually is the
        hostname and `localhost`)."""
        result = set()
        override = config.get_method(str, "local", "domains")
        if override is None:
            result.add(socket.gethostname())
            result.add(socket.getfqdn())
            result.add("localhost")

        extra = config.get_method(str, "local", "extra_domains")
        for conf in (override, extra):
            if conf is None: continue
            result |= self.parse_domains(conf)

        return result

    def parse_domains(self, domains):
        """Return a set containing all domains from the comma-separated string
        extracted from the configuration file."""
        return set(map(str.strip, domains.split(",")))

    def get_body(self):
        """Return the body of the message as a string."""
        return self.message.as_string(False)

def default_mailname():
    """Determine the default mailname by reading /etc/mailname or using the
    hostname."""
    fin = mailname = None
    try:
        fin = open("/etc/mailname")
        mailname = fin.read().strip()
    except IOError:
        if fin: fin.close()

    if not mailname:
        return socket.getfqdn()
    else:
        return mailname

# vim:tw=78:fo-=t:sw=4:sts=4:et:
