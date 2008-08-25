# -*- coding: utf-8 -*-
#
# This file is part of submit, a sendmail replacement or supplement for
# multi-user desktop systems.
#
# Copyright © 2008 Michael Schutte <michi@uiae.at>
#
# submit is available under the terms of the MIT/X license.  Please see the
# file COPYING for details.

import gettext as _gettext

__all__ = ["_", "n_", "gettext", "init_i18n"]

tr = None

def n_impl(string):
    """Do not translate a string, but mark it for inclusion in the .pot
    file."""
    return string

def gettext(string):
    """Translate a string."""
    if tr is None:
        return string
    else:
        return tr.lgettext(string)

n_ = n_impl
_ = gettext

def init_i18n():
    """Prepare gettext for internationalization."""
    global tr
    tr = _gettext.translation("submit", fallback=True)

# vim:tw=78:fo-=t:sw=4:sts=4:et:
