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
from submit.config import *
from submit.daemon import *
from submit.errors import *
from submit.i18n import *
from submit.message import *
from submit.ui import *
from cStringIO import StringIO
import sys
import os
import traceback

__all__ =  ["Frontend"]

class Frontend:
    """The submit frontend.  It either delivers mails on its own or starts and
    communicates with the daemon process to do so."""

    def __init__(self, usage):
        """Create a new frontend instance."""
        self.usage = usage
        self.config = None

        self.daemon_only = False
        self.shutdown = False
        self.unlock_method = None
        self.config_location = None
        self.envelope_from = None
        self.period_eof = True
        self.recipients = []
        self.parse_rcpts = False

        self.channel = None
        self.ui = None

    def run(self):
        """Parse command line options, read the message and submit it.  This
        method does not return."""
        self.getopt()
        self.config = Config(self.config_location)

        if self.shutdown:
            if self.connect():
                self.channel.send(ShutdownRequest())
            sys.exit(0)

        self.setup_ui()

        force_daemon = self.config.get_general(bool, "force_daemon", False)
        if not self.connect() and force_daemon:
            self.fork_daemon()
            self.connect()

        # -bd: start the daemon, if necessary, and test the connection
        if self.daemon_only:
            if not self.channel:
                self.fork_daemon()
                self.connect()
            self.channel.send(None)
            sys.exit(0)

        # --unlock: ask for some passwords, then quit
        elif self.unlock_method:
            method = self.unlock_method
            if method == "all": method = None
            if not self.deliver(UnlockRequest(method)):
                sys.exit(1)

        # normal mode of operation: read a message and send it
        else:
            msg = self.read_message()
            if not self.deliver(msg):
                sys.exit(1)

        sys.exit(0)

    def getopt(self):
        """Parse options."""
        args = sys.argv[1:]

        def get_arg(opt, length=2):
            """Get the option argument out of something like -fuser (remove
            `length` characters from the beginning of `opt`).  If the option
            is empty, pop the next argument from the command line."""
            arg = opt[length:]
            if arg:
                return arg
            else:
                return args.pop(0)

        try:
            while len(args) > 0:
                opt = args.pop(0)
                if opt == "--":
                    break
                elif opt in ("-bd", "--daemon"):
                    self.daemon_only = True
                elif opt == "--unlock":
                    self.unlock_method = args.pop(0)
                elif opt == "--shutdown":
                    self.shutdown = True
                elif opt[:2] == "-C":
                    self.config_location = get_arg(opt)
                elif opt[:2] in ("-f", "-r"):
                    self.envelope_from = get_arg(opt)
                elif opt in ("-i", "-oi"):
                    self.period_eof = False
                elif opt == "-t":
                    self.parse_rcpts = True
                elif opt == "-q":
                    sys.exit(0)
                elif opt in ("-G", "-m", "-n", "-U"):
                    # ignore these options
                    pass
                elif opt[:2] in ("-A", "-b", "-F", "-h", "-L", "-N", "-R",
                        "-X", "-o"):
                    # ignore these options and their arguments
                    get_arg(opt)
                elif opt == "--help":
                    print gettext(self.usage)
                    sys.exit(0)
                elif opt == "--version":
                    print "submit %s" % SUBMIT_VERSION
                    sys.exit(0)
                elif opt.startswith("-"):
                    print >>sys.stderr, _('Unknown option: "%s".') % opt
                    sys.exit(2)
                else:
                    self.recipients.append(opt)
        except IndexError:
            print >>sys.stderr, _('Option "%s" needs an argument.') % opt
            sys.exit(2)

        # after “--”, only recipient addresses are left
        self.recipients += args

    def setup_ui(self):
        """Find a suitable user interface for password queries and error
        messages."""
        uinames = self.config.get_general(str, "ui", "gnome,gtk,tty")
        for uiname in uinames.split(","):
            uiname = uiname.strip() + "_ui"
            try:
                mod = __import__("submit.ui.%s" % uiname)
            except ImportError:
                continue
            try:
                self.ui = getattr(getattr(mod, "ui"), uiname).Interface()
            except InterfaceError:
                continue
            break
        if self.ui: self.ui.prepare()

    def connect(self):
        """Establish a connection with the daemon socket, if available."""
        try:
            self.channel = Channel.connect(self.config)
            request = self.channel.receive()
            if request.version != SUBMIT_VERSION:
                # we probably have been upgraded since the daemon is running
                self.channel.send(ShutdownRequest())
                self.channel = None
                self.fork_daemon()
                self.channel = Channel.connect(self.config)
                request = self.channel.receive()
                if request.version != SUBMIT_VERSION:
                    print >>sys.stderr, """\
The version numbers of submit and the daemon process do not match. Please
check your installation."""
                    sys.exit(1)
            return True
        except ChannelError:
            self.channel = None
            return False

    def fork_daemon(self):
        """Start the daemon process."""
        if self.channel: return     # there already is a connection to the daemon
        sockfile = self.config.path(self.config.get_general(str, "socket", "socket"))
        daemon = Daemon(self.config, sockfile)
        daemon.run()

    def read_message(self):
        """Read the message from stdin."""
        body = StringIO()
        while True:
            line = sys.stdin.readline()
            if line == "": break
            if line.rstrip("\r\n") == "." and self.period_eof: break
            body.write(line)
        body = body.getvalue()
        return Message(self.config, body, self.recipients, self.parse_rcpts,
                self.envelope_from)

    def deliver(self, message):
        """Try to send the given message by either communicating with the
        daemon process or by directly sending it.  `message` can also be an
        `UnlockRequest` if the user has requested to authenticate without
        sending a message."""
        if not self.channel:
            use_daemon = False
            deliverers = message.create_deliverers(self.config)
            # if the chosen UI does not store passwords itself and at least
            # one deliverer is likely to ask for a password, better launch and
            # use the daemon
            if not self.ui or not self.ui.stores_passwords():
                if isinstance(message, UnlockRequest):
                    use_daemon = True
                else:
                    for deliverer, rcpts in deliverers:
                        if deliverer.needs_authentication():
                            use_daemon = True
                            break
        else:
            use_daemon = True
        if use_daemon:
            return self.deliver_daemon(message)
        else:
            return self.deliver_directly(message, deliverers)

    def deliver_daemon(self, message):
        """Use the daemon process to deliver `message`."""
        if not self.channel:
            self.fork_daemon()
            self.connect()

        ch = self.channel
        broken = False
        ch.send(self.config)
        while True:
            request = ch.receive()
            if isinstance(request, MessageRequest):
                ch.send(message)
            elif isinstance(request, PasswordRequest):
                try:
                    password = self.ask_password(
                            request.method, request.key,
                            request.query, request.first)
                except InterfaceError:
                    broken = True
                    password = None
                ch.send(request.create_response(password))
            elif isinstance(request, UserError):
                if broken:
                    # the error says that delivery was aborted “on user
                    # request”, when the real problem is that no UI is
                    # available — don’t show a message
                    pass
                else:
                    self.show_error(request)
                return False
            elif isinstance(request, InternalError):
                print >>sys.stderr, "Internal error: " + str(request.exception)
                sys.stderr.write("\n".join(traceback.format_list(request.traceback)))
                return False
            elif isinstance(request, CloseRequest):
                return True

    def deliver_directly(self, message, deliverers):
        """Use the given deliverers to submit `message` directly (i.e.,
        without using a daemon)."""
        for deliverer, rcpts in deliverers:
            store = PasswordStore(deliverer.method)
            try:
                deliverer.authenticate(FrontendAuthenticator(store, self))
                if self.unlock_method:
                    deliverer.abort()
                else:
                    deliverer.deliver(message, rcpts)
            except InterfaceError:
                deliverer.abort()
                return False
            except UserError, e:
                deliverer.abort()
                self.show_error(e)
                return False
        return True

    def ask_password(self, method, key, query, first):
        """Ask the user for the specified password.  If no user interface is
        available, raise an `InterfaceError`."""
        if self.ui:
            return self.ui.ask_password(method, key, query, first)
        else:
            print >>sys.stderr, _("""\
Mail submission has been cancelled because you have to supply a password, but
there is no way to ask you for it.  This happens, for example, if you run a
mail client like Mutt on a console.

Please run "submit --unlock all" on another virtual terminal and try again.""")
            raise InterfaceError, "no UI available"

    def show_error(self, error):
        """Show an error message."""
        if self.ui:
            self.ui.show_error(error)
        else:
            print >>sys.stderr, str(error)

class FrontendAuthenticator(AbstractAuthenticator):
    """An authenticator used as a daemonless provider of credentials.  It
    directly passes on password requests to the frontend."""

    def __init__(self, store, frontend):
        """Create a new frontend authenticator."""
        AbstractAuthenticator.__init__(self, store)
        self.frontend = frontend

    def query_password(self, key, query, first):
        """Ask the user for a password."""
        return self.frontend.ask_password(self.store.method, key, query, first)

# vim:tw=78:fo-=t:sw=4:sts=4:et:
