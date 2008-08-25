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

__all__ = ["AbstractDeliverer"]

class AbstractDeliverer:
    """An abstract deliverer.  Deliverers submitting to sendmail programs or
    SMTP servers are derived from this class."""

    def __init__(self, config, method):
        """Initialize a deliverer responsible for transmitting a `message` to
        some recipients.  Configuration parameters should be retrieved from
        the `method` delivery section via the given `Config` instance."""
        self.config = config
        self.method = method

    def needs_authentication(self):
        """Find out whether manual password input is likely to be needed."""
        raise NotImplementedError, "abstract needs_authentication() called"

    def authenticate(self, auth):
        """Do everything needed to get the rights to submit the message.  The
        given `Authenticator` provides the functions needed for obtaining
        passwords and/or passphrases."""
        raise NotImplementedError, "abstract authenticate() called"

    def deliver(self, message, rcpts):
        """Transmit the message.  `authenticate` will always be called
        immediately before this method.  If a network socket gets opened in
        `authenticate`, there is no need to worry about timeouts."""
        raise NotImplementedError, "abstract deliver() called"

    def abort(self):
        """Close the connection properly after authentication.  This method is
        called *instead of* `deliver` if the authentication has failed or if
        there is no message to deliver (unlock mode)."""
        raise NotImplementedError, "abstract abort() called"

# vim:tw=78:fo-=t:sw=4:sts=4:et:
