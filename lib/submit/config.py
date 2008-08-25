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
from ConfigParser import SafeConfigParser
import os
import socket

__all__ = ["Config"]

DEFAULT_CONFIG_PATH = os.path.expanduser("~/.submit")

class Config:
    """The configuration store.  Configuration files are looked for in
    /etc/submit/config and ~/.submit/config (if no other file name was
    specified by the user)."""

    def __init__(self, confdir = None):
        """Load a configuration file.  If an explicit `confdir` is given, the
        `config` file in there is read.  Otherwise, ~/.submit/config is
        tried; if it doesn’t exist, no configuration is loaded at all."""
        self.config = SafeConfigParser()
        if confdir:
            self.confdir = confdir
            self.load_config(os.path.join(confdir, "config"))
        else:
            self.confdir = DEFAULT_CONFIG_PATH
            try: self.load_config(os.path.join(DEFAULT_CONFIG_PATH, "config"))
            except IOError: pass

    def load_config(self, filename):
        """Load a configuration file.  If it does not exist (or cannot be
        read), the IOError is passed through."""
        with file(filename, "r") as fin:
            self.config.readfp(fin, filename)

    def get_general(self, tpe, name, default = None):
        """Retrieve a value from the general section.  See `get`."""
        return self.get(tpe, "general", name, default)

    def get_methods(self):
        """Return the name of all sections starting with `method `."""
        return [i[7:] for i in self.config.sections() if i.startswith("method ")]

    def get_method(self, tpe, section, name, default = None):
        """Retrieve a value from the given delivery method `section`, for
        example, `local` or `remote`.  See `get`."""
        return self.get(tpe, "method " + section, name, default)

    def get(self, tpe, section, name, default = None):
        """Retrieve a value from the given `section`, typed `tpe`
        (`string`, `int`, `float` or `boolean`).  If there is no matching key,
        return `default`; if that is a function, return its result when called
        without parameters."""
        value = None
        if not self.config.has_option(section, name):
            pass
        elif tpe is int:
            value = self.config.getint(section, name)
        elif tpe is float:
            value = self.config.getfloat(section, name)
        elif tpe is bool:
            try: value = self.config.getboolean(section, name)
            except ValueError: pass
        else:
            value = self.config.get(section, name)

        if value is None:
            if callable(default):
                value = default()
            else:
                value = default

        return value

    def path(self, filename):
        """Determine the absolute path to `filename`, which is either returned
        unchanged if it is already absolute, or interpreted as relative to the
        location of the configuration file used to create this `Config`
        object."""
        filename = os.path.expanduser(filename)
        if os.path.isabs(filename):
            return filename
        return os.path.join(self.confdir, filename)

    def file(self, filename, *args):
        """Use `path` to determine the path to `filename` and open it as a
        file.  `args` are passed through to the builtin `file` function."""
        return file(self.path(filename), *args)

    def create_deliverer(self, method, default="sendmail"):
        """Create a matching deliverer for the given delivery method."""
        modname = self.get_method(str, method, "type", default)
        try:
            mod = __import__("submit.deliverers.%s" % modname)
        except ImportError:
            raise ConfigError(
                    n_('The delivery type "%s" is not defined.'), modname)
        mod = getattr(getattr(mod, "deliverers"), modname)
        return mod.Deliverer(self, method)

# vim:tw=78:fo-=t:sw=4:sts=4:et:
