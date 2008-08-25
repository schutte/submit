# -*- coding: utf-8 -*-
#
# This file is part of submit, a sendmail replacement or supplement for
# multi-user desktop systems.
#
# Copyright © 2008 Michael Schutte <michi@uiae.at>
#
# submit is available under the terms of the MIT/X license.  Please see the
# file COPYING for details.

from __future__ import with_statement
from submit.errors import *
from submit.deliverers import *
from submit.i18n import *
from contextlib import *
import threading
import time

__all__ = ["PasswordStore", "AbstractAuthenticator", "UnlockRequest",
        "PasswordRequest", "PasswordResponse",
        "AuthenticationCancelledResponse"]

class PasswordStore:
    """The password cache used by an authenticator.  It holds passwords in
    memory for a configurable amount of time.

    There is one `PasswordStore` per delivery method section."""

    def __init__(self, method):
        """Create a `PasswordStore` without any stored passwords."""
        self.method = method
        self.passwords = {}
        self.lock = threading.Lock()
        self.last_access = None

    def expire(self, timeout):
        """If the last access to the password store was more than `timeout`
        seconds ago, purge the stored data."""
        if self.last_access is None: return
        now = time.time()
        if (now < self.last_access) or (now - self.last_access > timeout):
            with self:
                self.clear()

    def __enter__(self):
        """Acquire the lock.

        Use instances of `PasswordStore` in a `with` clause to get locking."""
        self.lock.acquire()

    def __exit__(self, *exc_info):
        """Release the lock."""
        self.lock.release()
        self.last_access = time.time()

    def clear(self):
        """Remove all stored passwords."""
        self.passwords.clear()

    def get(self, config, key, default = None):
        """Obtain the password `key` from the cache or from the configuration
        file.  If it cannot be found in neither of them, return the default
        value."""
        password = self.passwords.get(key)
        if password is None:
            password = config.get_method(str, self.method, key)
        elif password == "":
            password = None
        if password is None:
            return default
        else:
            self.put(key, password)
        return password

    def tried_before(self, key):
        """Determine whether authentication with a given key has been tried
        before.  This returns true even after `remove` has been called, but
        not after `clean`."""
        return (self.passwords.get(key, None) is not None)

    def put(self, key, password):
        """Store a (key, password) association."""
        self.passwords[key] = password

    def remove(self, key):
        """Remove a (key, password) association (keeping the information that
        the password from the configuration file has already been tried)."""
        self.passwords[key] = ""

class AbstractAuthenticator:
    """When a deliverer detects that the transmission of credentials is
    needed, it invokes the `get_password` method.  The authenticator takes
    care of asking the frontend to present a query to the user and then stores
    passwords in memory for a configurable amount of time.

    There is one authenticator per delivery method section and deliverered
    message."""

    def __init__(self, store):
        """Create a new authenticator using the given password `store`."""
        self.store = store

    def get_password(self, config, key, query):
        """Retrieve the password called `key` (something like
        `key_passphrase`).  If necessary, `query` is transferred to the
        frontend and will end up somewhere on whatever type of display the
        user is using."""
        with self.store:
            password = self.store.get(config, key)
            if not password:
                first = not self.store.tried_before(key)
                password = self.query_password(key, query, first)
                if password is None:
                    raise AuthenticationFailedError(
                            n_("Aborted on user request."))
                self.store.put(key, password)
        return password

    def remove_password(self, key):
        """Remove the stored password given by `key` from the underlying
        password store.  Use this to let the user try to specify a password
        repeatedly: delete the stored credentials between the attempts."""
        with self.store:
            self.store.remove(key)

    def query_password(self, key, query, first):
        """Override this method in subclasses to somehow ask the user for
        their credentials."""
        raise NotImplementedError, "abstract query_password() called"

class UnlockRequest:
    """Ask for one or all delivery methods to be unlocked.  This simply means
    that an authentication process is started with the requested method(s),
    but no message is actually delivered.  If all `PasswordRequest`s are
    answered properly, all necessary passwords are stored, and the user can
    send mails without having to type them again."""

    def __init__(self, method = None):
        """Create an unlocking request for the given `method` (or all methods
        if `None`)."""
        self.method = method

    def create_deliverers(self, config):
        """Create the deliverers for the method(s) to be unlocked.  A list of
        (deliverer, None) tuples is returned."""
        if self.method:
            return [(config.create_deliverer(self.method), None)]
        else:
            result = []
            for method in config.get_methods():
                result.append((config.create_deliverer(method), None))
            return result

class PasswordRequest:
    """Tell the frontend to ask the user for a password."""

    def __init__(self, method, key, query, first):
        """A password request for `key` sent by the deliverer identified by
        `method`. `query` is the `gettext`-able message to display.  The
        parameters are made available in member variables with the same
        names."""
        self.method = method
        self.key = key
        self.query = query
        self.first = first

    def create_response(self, password):
        """Create a `PasswordResponse` object which can be sent back to the
        daemon."""
        if password is None:
            return AuthenticationCancelledResponse()
        else:
            return PasswordResponse(password)

class PasswordResponse:
    """This message is sent by the client after the user has entered a
    password."""

    def __init__(self, password):
        """Create a password response message containing the given password in
        its `password` field."""
        self.password = password

class AuthenticationCancelledResponse:
    """The user refused to authenticate; cancel delivery."""

# vim:tw=78:fo-=t:sw=4:sts=4:et:
