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
from submit.ui import *
import os

try:
    import gtk
except ImportError:
    gtk = None

__all__ = ["GTKInterface"]

class GTKInterface(AbstractInterface):
    """A GTK+-based interface."""

    def check(self):
        """Determine whether PyGTK is available and usable."""
        return (gtk is not None) and (os.environ.has_key("DISPLAY"))

    def prepare(self):
        """No-op."""

    def show_error(self, error):
        """Display an error message."""
        dlg = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_CANCEL,
                message_format=gettext(error.message) % error.params)
        dlg.set_position(gtk.WIN_POS_CENTER)
        dlg.set_title(gettext("Mail delivery problem"))
        dlg.run()
        dlg.destroy()
        while gtk.events_pending():
            gtk.main_iteration()

    def ask_password(self, method, key, message, first):
        """Query for a password."""
        return self.password_dialog(method, key, message, first, False)[0]

    def password_dialog(self, method, key, message, first, saveoption):
        """Ask the user for his password.  If `saveoption` is true, a checkbox
        which allows the user to store their password permanently will be
        added to the interface.  The return value is (`password`, `store`)."""
        dlg = gtk.Dialog(title=self.ask_password_title(method),
                buttons=(gtk.STOCK_CANCEL,  gtk.RESPONSE_REJECT,
                         gtk.STOCK_OK,      gtk.RESPONSE_ACCEPT))
        dlg.set_default_response(gtk.RESPONSE_ACCEPT)
        dlg.set_position(gtk.WIN_POS_CENTER)

        hbox = gtk.HBox(spacing=8)
        hbox.set_border_width(6)
        dlg.vbox.pack_start(hbox)
        hbox.pack_start(gtk.image_new_from_stock(
            gtk.STOCK_DIALOG_AUTHENTICATION, gtk.ICON_SIZE_DIALOG))
        vbox = gtk.VBox(spacing=8)
        hbox.pack_end(vbox)

        vbox.pack_start(gtk.Label(gettext(message)))
        entry = gtk.Entry()
        entry.set_visibility(False)
        entry.set_activates_default(True)
        vbox.pack_start(entry)

        if saveoption:
            savecheck = gtk.CheckButton(_("Remember password"))
            vbox.pack_end(savecheck)

        dlg.vbox.show_all()

        if dlg.run() == gtk.RESPONSE_ACCEPT:
            password = entry.get_text()
        else:
            password = None
        dlg.destroy()
        while gtk.events_pending():
            gtk.main_iteration()
        return (password, saveoption and savecheck.get_active())

    def stores_passwords(self):
        """This UI cannot store passwords itself."""
        return False

Interface = GTKInterface

# vim:tw=78:fo-=t:sw=4:sts=4:et:
