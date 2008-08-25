# -*- coding: utf-8 -*-
#
# This file is part of submit, a sendmail replacement or supplement for
# multi-user desktop systems.
#
# Copyright © 2008 Michael Schutte <michi@uiae.at>
#
# submit is available under the terms of the MIT/X license.  Please see the
# file COPYING for details.

class UserError(Exception):
    """An error with an internationalizable message which is of potential
    interest to the user."""

    def __init__(self, message, params = ()):
        """Create a new UserError.  `message` sets the
        (internationalizable) message text, `params` can be an enumeration of
        additional strings for %-substitution of the translated message."""
        Exception.__init__(self, message)
        if params is str:
            self.params = (params, )
        else:
            self.params = params

    def __str__(self):
        return self.message % self.params

class DeliveryError(UserError):
    """Something went wrong in the delivery process."""

class AuthenticationFailedError(DeliveryError):
    """The authentication process failed."""

class DeliveryFailedError(DeliveryError):
    """The message submission failed."""

class ConfigError(UserError):
    """The user made a mistake in the configuration file."""

# vim:tw=78:fo-=t:sw=4:sts=4:et:
