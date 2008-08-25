# -*- coding: utf-8 -*-
#
# This file is part of submit, a sendmail replacement or supplement for
# multi-user desktop systems.
#
# Copyright © 2008 Michael Schutte <michi@uiae.at>
#
# submit is available under the terms of the MIT/X license.  Please see the
# file COPYING for details.

from submit import *
from submit.auth import *
from submit.channel import *
from submit.deliverers import *
from submit.errors import *
from submit.i18n import *
import sys
import os
from select import select
import threading
import traceback

__all__ =  ["Daemon"]

class Daemon:
    """Implementation of the submit daemon.  Accepts mails and passes them on
    to deliverers, which themselves pipe them to sendmail programs or transfer
    them over the network."""

    def __init__(self, config, sockfile = None):
        """Create a new daemon instance."""
        self.config = config
        self.sockfile = sockfile
        self.server = None
        self.passstores = {}

    def run(self):
        """Become a daemon and enter the mainloop."""
        pin, pout = os.pipe()
        if os.fork() != 0:
            # wait for the socket to become available
            os.read(pin, 1)
            os.close(pin)
            return

        try:
            os.setsid()
            if os.fork() != 0:
                sys.exit(0)
            os.chdir("/")
            devnull = os.open(os.devnull, os.O_RDWR)
            for fd in xrange(0, 3):
                try: os.close(fd)
                except IOError: pass
                os.dup2(devnull, fd)
            self.setup_socket()
            os.write(pout, ".")
            os.close(pout)
            self.mainloop()
        finally:
            sys.exit(0)

    def setup_socket(self):
        """Create the server socket."""
        self.server = Channel.setup(self.config, self.sockfile)

    def mainloop(self):
        """Wait for clients and start threads to handle them."""
        killin, killout = os.pipe()
        if self.server is None: self.setup_socket()
        while True:
            rlist, wlist, xlist = select([self.server, killin], [], [])
            if self.server in rlist:
                client, addr = self.server.accept()
                thd = threading.Thread(target=self.handle, args=(Channel(client), killout))
                thd.setDaemon(True)
                thd.start()
            if killin in rlist:
                # a thread wants us to go down
                os.read(killin, 1)
                os.close(killin)
                return

    def handle(self, client, killpipe):
        """Talk to a client."""
        try:
            client.send(ConfigRequest(SUBMIT_VERSION))
            config = client.receive()
            if config is None:  # just a connection test, never mind
                client.send(CloseRequest())
                return
            elif isinstance(config, ShutdownRequest):
                # bring down the main thread
                os.write(killpipe, ".")
                os.close(killpipe)
                return

            client.send(MessageRequest())
            msg = client.receive()

            try:
                self.deliver(client, config, msg)
                if isinstance(msg, UnlockRequest):
                    client.send(CloseRequest())
                else:
                    client.send(DeliverySuccessMessage())
            except UserError, e:
                client.send(e)
        except EOFError:
            pass
        except Exception, e:
            try: client.send(InternalError(e,
                traceback.extract_tb(sys.exc_info()[2])))
            except: pass
        finally:
            client.close()

    def deliver(self, client, config, message):
        """Message delivery: Deal with submission protocols and ask for
        necessary passwords.  `message` can be a `Message` or an
        `UnlockRequest`"""
        deliverers = message.create_deliverers(config)
        for deliverer, rcpts in deliverers:
            store = self.get_password_store(config, deliverer.method)
            try:
                deliverer.authenticate(ChannelAuthenticator(store, client))
                if isinstance(message, UnlockRequest):
                    deliverer.abort()
                else:
                    deliverer.deliver(message, rcpts)
            except UserError, e:
                deliverer.abort()
                raise

    def get_password_store(self, config, method):
        """Get the password store for the given delivery method.  If there is
        none yet, create an empty one."""
        store = self.passstores.get(method)
        if not store:
            store = self.passstores[method] = PasswordStore(method)
        else:
            # clean up stored passwords, if necessary
            timeout = config.get_method(int, method, "expire")
            if not timeout:
                timeout = config.get_general(int, "expire", 60)
            store.expire(60 * timeout)
        return store

class ChannelAuthenticator(AbstractAuthenticator):
    """An authenticator forwarding password requests to the frontend
    process."""

    def __init__(self, store, channel):
        """Create a new channel-based authenticator."""
        AbstractAuthenticator.__init__(self, store)
        self.channel = channel

    def query_password(self, key, query, first):
        """Ask for the passphrase on the channel connected with the client."""
        self.channel.send(PasswordRequest(self.store.method, key, query, first))
        response = self.channel.receive()
        if isinstance(response, PasswordResponse):
            return response.password
        else:
            return None

# vim:tw=78:fo-=t:sw=4:sts=4:et:
