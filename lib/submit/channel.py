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
import os
import socket
import pickle
import struct

__all__ = ["Channel", "ChannelError", "ConfigRequest", "MessageRequest",
        "CloseRequest", "ShutdownRequest", "DeliverySuccessMessage",
        "InternalError"]

LENGTH_FORMAT = "!L"        # transfer chunk length as C unsigned long
LENGTH_SIZE = struct.calcsize(LENGTH_FORMAT)    # sizeof(unsigned long)
LONG_MAX = 256 ** LENGTH_SIZE - 1               # LONG_MAX

class ChannelError(Exception):
    """Something went wrong in the communication process."""

class Channel:
    """submit frontends and the daemon process communicate over a socket in
    the UNIX domain.  They do so by sending and receiving pickled objects.
    This class wraps a socket and represents an endpoint of a communication
    channel."""

    def __init__(self, socket):
        """Set up this channel endpoint."""
        self.socket = socket

    @classmethod
    def get_path(cls, config):
        """Determine the path to the UNIX domain socket, which is specified by
        the configuration key `general.socket` (default
        `~/.submit/socket`)."""
        return config.get_general(str, "socket",
                os.path.expanduser("~/.submit/socket"))

    @classmethod
    def setup(cls, config, filename = None):
        """Create the socket."""
        if filename is None:
            filename = cls.get_path(config)
        if os.path.exists(filename):
            os.remove(filename)
        srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        srv.bind(filename)
        srv.listen(1)
        return srv

    @classmethod
    def connect(cls, config):
        """Open the socket and return a `Channel` instance allowing
        communication with the daemon process.

        A `ChannelError` will be raised if there is no channel yet, which
        in most cases means that the daemon has not been started yet."""
        filename = cls.get_path(config)
        if not os.path.exists(filename):
            raise ChannelError, "channel does not exist"
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try: sock.connect(filename)
        except socket.error, e:
            if e.args[0] == 111:
                raise ChannelError, "channel refuses connection"
            else:
                raise e
        return cls(sock)

    def receive(self):
        """Receive a pickled object and return a `load`ed instance."""
        s = ""
        while True:
            try:
                length = self.socket.recv(LENGTH_SIZE)
                if not length:
                    raise EOFError
            except socket.error:
                raise EOFError

            length = struct.unpack(LENGTH_FORMAT, length)[0]
            if length == 0:
                break
            s += self.socket.recv(length)

        return pickle.loads(s)

    def send(self, msg):
        """Send a `msg` to the peer, pickle-`dump`ing it before
        transmission."""
        smsg = pickle.dumps(msg)
        while True:
            s = smsg[:LONG_MAX]
            length = len(s)
            self.socket.sendall(struct.pack(LENGTH_FORMAT, length))
            if length != 0: self.socket.sendall(s)
            else: break
            smsg = smsg[length:]

    def close(self):
        """Close the underlying socket."""
        self.socket.close()

class ConfigRequest:
    """Demand a `Config` object and announce the version number of the daemon
    process."""

    def __init__(self, version):
        self.version = version

class MessageRequest:
    """Demand transfer of the message to be submitted."""

class CloseRequest:
    """Close the connection."""

class ShutdownRequest:
    """Tell the daemon to go down."""

class DeliverySuccessMessage(CloseRequest):
    """Notify about the successful delivery of the message."""

class InternalError(CloseRequest):
    """Something went horribly wrong.  Instances of this message class contain
    an exception object and a traceback."""

    def __init__(self, exception, traceback):
        """Create a new internal error message."""
        self.exception = exception
        self.traceback = traceback

# vim:tw=78:fo-=t:sw=4:sts=4:et:
