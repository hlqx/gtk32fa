# main.py
#
# Copyright 2020 Niall Asher
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Handy', '1')
from gi.repository import Gtk, Gio, Gdk, GLib, Handy, GdkPixbuf
from gi.repository.Handy import Window
import cairo
import pyotp
import threading
import base64
import hashlib
import pathlib
import os
import html
import json
import sqlite3
from time import time
from uuid import uuid4
from operator import itemgetter
from cryptography.fernet import Fernet, InvalidToken
from time import sleep
from .listbox import TwoFactorListBoxRow
from .twofactorcode import TwoFactorCode, TwoFactorUIElements
from .screenshot import GNOMEScreenshot
from .logger import InfoLogger
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GObject, GLib, Gio


class MainApplication(Gtk.Application):

    def __init__(self):
        InfoLogger.stdout_log("Starting twofactor [debug build]", "wait")
        GObject.threads_init()
        # Register on DBus
        super().__init__(application_id='com.niallasher.twofactor',
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.gtkbuilder = Gtk.Builder()
        # Register handy types with the gtkbuilder
        Handy.init()
        self.authentication_sizegroup = Gtk.SizeGroup.new(Gtk.SizeGroupMode.HORIZONTAL)
        self.increment_sizegroup = Gtk.SizeGroup.new(Gtk.SizeGroupMode.HORIZONTAL)
        self.gtkbuilder.add_from_resource("/com/niallasher/twofactor/window.ui")
        # get widgets using gtk.builder
        self.application_window = self.gtkbuilder.get_object("application_window")
        self.main_stack = self.gtkbuilder.get_object("mainstack")
        self.headerbar = self.gtkbuilder.get_object("headerbar")
        self.hb_lstack = self.gtkbuilder.get_object("hb_lstack")
        self.hb_rstack = self.gtkbuilder.get_object("hb_rstack")
        self.hbls_backbtn = self.gtkbuilder.get_object("hbls_backbtn")
        self.hb_editmode = self.gtkbuilder.get_object("hb_editmode")
        self.an_pop = self.gtkbuilder.get_object("an_popover")
        self.prefs_dmslide = self.gtkbuilder.get_object("prefs_dmslide")
        self.prefs_hiddensecret = self.gtkbuilder.get_object("prefs_hiddensecret")
        self.prefs_cleardata = self.gtkbuilder.get_object("prefs_cleardata")
        self.mainlistbox = self.gtkbuilder.get_object("mainlistbox")
        self.ns_counterlbl = self.gtkbuilder.get_object("ns_counterlbl")
        self.ns_countersb = self.gtkbuilder.get_object("ns_countersb")
        self.ns_secretentry = self.gtkbuilder.get_object("ns_secretentry")
        self.ns_add = self.gtkbuilder.get_object("ns_add")
        self.ns_name_buffer = self.gtkbuilder.get_object("ns_name_buffer")
        self.ns_issuer_buffer = self.gtkbuilder.get_object("ns_issuer_buffer")
        self.ns_secret_bufffer = self.gtkbuilder.get_object("ns_secret_buffer")
        self.ns_secret_entry = self.gtkbuilder.get_object("ns_secret_entry")
        self.ns_issuer_entry = self.gtkbuilder.get_object("ns_issuer_entry")
        self.ns_name_entry = self.gtkbuilder.get_object("ns_name_entry")
        self.aboutdialog = self.gtkbuilder.get_object("aboutdlg")
        self.crf_progress = self.gtkbuilder.get_object("crf_progress")
        self.import_code_btn = self.gtkbuilder.get_object("btn_importcodes")
        self.choose_image_btn = self.gtkbuilder.get_object("btn_chooseimage")
        self.clear_image_btn_revealer = self.gtkbuilder.get_object("revealer_clearimagebtn")
        self.crf_progress.set_fraction(1)
        self.mainlistbox.get_style_context().add_class("codelistbox")
        self.newlistboxrow4 = self.gtkbuilder.get_object("newlistbox_row_4")
        self.preview_avatar = self.gtkbuilder.get_object("preview_avatar")
        self.listbox_scrolledwindow = self.gtkbuilder.get_object("listbox_scrolledwindow")
        self.spinner = self.gtkbuilder.get_object("spinner")
        self.spinner.hide()
        # connect handlers using a dict
        handlers = {
            "winclosed": Gtk.main_quit,
            "an_totp_press": self.new_code_totp,
            "an_hotp_press": self.new_code_hotp,
            "hb_prefs_press": self.hb_prefs_press,
            "hb_editmode_press": self.hb_editmode_press,
            "hbls_back_press": self.hb_back_press,
            "prefs_clear_data_click": self.prefs_clear_data_click,
            "prefs_dmslide_slide": self.prefs_dmslide_slide,
            "prefs_hiddensecret_slide": self.prefs_hiddensecret_slide,
            "ns_add_press": self.ns_add_press,
            "ns_issuer_change": self.ns_issue_change,
            "ns_name_change": self.ns_name_change,
            "ns_secret_change": self.ns_secret_change,
            "ns_entr_press": self.newcode_enter_press,
            "about_btn_press": self.about_btn_press,
            "btn_importcodes_clicked": self.import_code,
            "btn_chooseimage_clicked": self.choose_image,
            "btn_clearimage_click": self.clear_image
        }
        # other things
        self.darktheme = False
        self.gtkbuilder.connect_signals(handlers)
        self.codes = {}
        self.editing = [False, None, None]
        self.crypto = None
        self.crypto_key = None
        self.new_code_type = None
        self.editmode = False
        self.secret_ok = False
        self.name_ok = False
        self.issuer_ok = False
        # create a clipboard object, so that we can copy codes to it later
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        # create a gtksettings object to retrieve keys from GSettings
        self.gtksettings = Gtk.Settings().get_default()
        # target entry for drag'n'drop
        self.targetEntry = Gtk.TargetEntry.new('GTK_LIST_BOX_ROW',
                                               Gtk.TargetFlags.SAME_APP,
                                               0)
        # set the mainlistbox as a drag destination
        self.mainlistbox.drag_dest_set(Gtk.DestDefaults.DROP | Gtk.DestDefaults.MOTION,
                         [self.targetEntry],
                         Gdk.DragAction.MOVE)
        self.mainlistbox.connect("drag-data-received", self.drag_data_recieved)
        self.mainlistbox.connect("drag-motion", self.drag_motion)
        # create a css provider to manage custom CSS GResources
        css_provider = Gtk.CssProvider()
        css_provider.load_from_resource("com/niallasher/twofactor/stylesheet.css")
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),
                                                 css_provider,
                                                 Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        code_validator = threading.Thread(target=self.code_checker,
                                          daemon=True)
        code_validator.start()
        # create settings object
        self.settings = Gio.Settings.new("com.niallasher.twofactor")
        self.load_config()
        Gtk.Window.__init__(self.application_window)
        #self.main_stack.set_visible_child_name("ms_import_types")
        #self.import_types_list_box = self.gtkbuilder.get_object("import_types_list_box")
        self._do_connect_database()
        self._do_check_database_integrity()
        threading.Thread(target=self._import_storage(), daemon=True)

    """
        Connect to an sqlite3 database located in XDG_CACHE_DIR/authwallet.db
        TODO: Figure out a better place for this that works well with flatpak & traditional methods
    """
    def _do_connect_database(self):
        cache_dir = GLib.get_user_data_dir()
        self.db_connection = sqlite3.connect(f"{cache_dir}/authwallet.db")
        self.db_cursor = self.db_connection.cursor()
        tableList = self.db_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
        if len(tableList) == 0:
            self._init_database()
        InfoLogger.stdout_log("Database Connected!", "info")

    """
        Create the authcodes table
    """
    def _init_database(self):
        # TODO: define proper schema for database
        InfoLogger.stdout_log("Creating database table...", "info")
        self.db_cursor.execute("CREATE TABLE authcodes (uuid TEXT, name TEXT, type TEXT, issuer TEXT, position INTEGER, code TEXT, image TEXT, counter INTEGER)")

    """
        Do a check_integrity check to ensure the database isn't obviously corrupted
    """
    def _do_check_database_integrity(self):
        self.db_cursor.execute("PRAGMA check_integrity;")
        # TODO: do something with this
        # TODO: remove this
        #self._database_test()

    """
        Parse keys from GSettings
    """
    def load_config(self):
        if self.settings.get_value('dark-theme').unpack():
            self.enable_dark_theme(True)
        else:
            self.enable_dark_theme(False)
        if self.settings.get_value('obscure-secrets').unpack():
            self.prefs_hiddensecret.set_active(True)
            self.ns_secret_entry.set_visibility(False)

    """
        Swap between general controls and no controls for the headerbar
    """
    def change_button_stack_state(self, enable=True):
        if enable:
            self.hb_lstack.set_visible_child_name("hbls_gctl")
            self.hb_rstack.set_visible_child_name("hbrs_gctl")
        elif not enable:
            self.hb_lstack.set_visible_child_name("hbls_noctl")
            self.hb_rstack.set_visible_child_name("hbrs_noctl")
        if len(self.codes) >= 1:
            self.hb_editmode.set_sensitive(True)
        else:
            self.hb_editmode.set_sensitive(False)

    """
        Import codes from program database
    """
    def _import_storage(self):
        self.db_cursor.execute("SELECT * from authcodes;")
        records = self.db_cursor.fetchall()
        for record in records:
            uuid = record[0]
            name = record[1]
            codetype = record[2]
            issuer = record[3]
            pos = record[4]
            secret = record[5]
            image = record[6] if record[6] != 'None' else None
            counter = record[7] if record[2] == 'hotp' else None
            self.mainlistbox.add(
                self.newlistrow({
                    'codetype': codetype,
                    'name': name,
                    'issuer': issuer,
                    'secret': secret,
                    'pos': pos,
                    'counter': counter,
                    'uuid': uuid,
                    'image': image
                })
            )
        InfoLogger.stdout_log(f"Loaded {len(self.codes)} code(s) from database", "success")

    """
        Inform GTK that the application wants a dark theme if it's avaliable
    """
    def enable_dark_theme(self, y=True):
        if y:
            self.darktheme = True
            self.prefs_dmslide.set_state(True)
            self.gtksettings.set_property("gtk-application-prefer-dark-theme", True)
            self.settings.set_value("dark-theme", GLib.Variant('b', True))
        elif not y:
            self.darktheme = False
            self.prefs_dmslide.set_state(False)
            self.gtksettings.set_property("gtk-application-prefer-dark-theme", False)
            self.settings.set_value("dark-theme", GLib.Variant('b', False))

    def new_code_hotp(self, _):
        self.new_code_type = "hotp"
        self.ns_hide_counter_options(False)
        self.newlistboxrow4.show()
        self.new_code_generic()

    def new_code_totp(self, _):
        self.new_code_type = "totp"
        self.newlistboxrow4.hide()
        self.ns_hide_counter_options(True)
        self.new_code_generic()

    """
        Generic requirements for a new code
    """
    def new_code_generic(self):
        self.hasimage = False
        self.an_pop.hide()
        self.change_button_stack_state(False)
        self.hb_lstack.set_visible_child_name("hbls_back")
        self.headerbar.set_show_close_button(False)
        self.hb_rstack.set_visible_child_name("hbrs_nexctl")
        self.main_stack.set_visible_child_name("ms_new")

    """
        Hide counter on the add code screen
        Useful for TOTP codes which don't require it
    """
    def ns_hide_counter_options(self, y=True):
        if y:
            self.ns_counterlbl.hide()
            self.ns_countersb.hide()
        elif not y:
            self.ns_countersb.show()
            self.ns_counterlbl.show()

    """
        Return to base state.
    """
    def ns_cancel_press(self, _):
        self.headerbar.set_show_close_button(True)
        self.change_button_stack_state(True)
        self.main_stack.set_visible_child_name("ms_main_list_box")
        self.ns_hide_counter_options(False)
        if True in self.editing:
            self.editing = [False, None, None]
        if self.new_code_type == 'hotp':
            self.ns_countersb.set_value(0)
        for x in self.codes:
            self.codes.get(x).ui.revealer.set_reveal_child(False)
        self.hb_editmode.set_active(False)
        self.new_code_type = None
        self.ns_secret_entry.set_text("")
        self.ns_name_entry.set_text("")
        self.ns_issuer_entry.set_text("")
        self.ns_add.set_label("Add")
        self.preview_avatar.set_image_load_func(self.avatar_load_blank)

    def ns_add_press(self, _):
        self.headerbar.set_show_close_button(True)
        self.ns_add_code()
        self.main_stack.set_visible_child_name("ms_main_list_box")
        self.change_button_stack_state(True)
        self.ns_add.set_label("Add")

    """
        Commit changes to database.
        Should be used threaded at all times.
    """
    def _db_commit(self):
        InfoLogger.stdout_log("Commiting database changes do disk...",  "wait")
        try:
            # TODO: only catch proper exceptions
            self.db_connection.commit()
            InfoLogger.stdout_log("Finished commiting database changes to disk.", "success")
        except:
            self.display_error("Failed to commit database changes!", log=True)

    """
        Display an error dialog to the user
        Will be displayed as a dialog, and logged to stdout if log=True.
    """
    # @param errortext The text that is displayed
    # @param log Whether the error is logged to stout
    def display_error(self, errortext, log=False):
        if log:
            InfoLogger.stdout_log(errortext, "failure")
        self.dialog = Gtk.MessageDialog(buttons=Gtk.ButtonsType.OK, parent=self.application_window, modal=True)
        self.dialog.set_markup(errortext)
        self.dialog.run()
        self.dialog.destroy()

    def ns_add_code(self):
        secret_plaintext = self.ns_secret_bufffer.get_text()
        secret_issuer = self.ns_issuer_buffer.get_text()
        secret_name = self.ns_name_buffer.get_text()
        while True:
            uuid = uuid4().__str__()
            if uuid in self.codes.keys():
                # loop if uuid is used
                pass
            else:
                break
        if True not in self.editing:
            # safe the pixbuf to pixbuf_buffer as a jpeg
            if self.hasimage:
                pixbuf_buffer = self.currentpixbuf.save_to_bufferv("png",
                                                               [],
                                                               [])
            codeinfo = {
                'codetype': self.new_code_type,
                'name': secret_name,
                'issuer': secret_issuer,
                'secret': secret_plaintext,
                'pos': len(self.codes) + 1,
                'counter': self.ns_countersb.get_value().__int__() if (self.new_code_type == 'hotp') else None,
                'uuid': uuid,
                'image': GLib.base64_encode(pixbuf_buffer[1]) if (self.hasimage) else None
            }
            print(codeinfo)
            self.mainlistbox.add(self.newlistrow(codeinfo))
            self.mainlistbox.show_all()
            self.db_cursor.execute(f"""INSERT INTO authcodes (uuid, name, type, issuer, position, code, image, counter)
                                   VALUES ('{codeinfo['uuid']}', '{codeinfo['name']}', '{codeinfo['codetype']}', '{codeinfo['issuer']}', '{codeinfo['pos']}', '{codeinfo['secret']}', '{codeinfo['image']}', '{codeinfo['counter']}')""")
            InfoLogger.stdout_log("Inserted entry into database", "info")
            self.db_cursor.execute("SELECT * from authcodes;")
            records = self.db_cursor.fetchall()
            threading.Thread(target=self._db_commit, daemon=False).run()
        elif True in self.editing:
            current_uuid = self.editing[1]
            modobj = self.codes.get(current_uuid)
            # don't show image if code doesn't have one
            if modobj.image is None:
                self.preview_avatar.set_image_load_func(self.avatar_load_blank)
                self.clear_image_btn_revealer.set_reveal_child(False)
            else:
                # TODO
                # FIXME move this
                # self.preview_avatar.set_image_load_func(self.avatar_load_func())
                self.clear_image_btn_revealer.set_reveal_child(True)
            # if the secret has changed, recalculate
            if self.ns_secret_entry.get_text() != modobj.codestr:
                modobj.codestr = self.ns_secret_entry.get_text()
                if self.editing[2] == 'totp':
                    modobj.code = pyotp.totp.TOTP(modobj.codestr)
                    modobj.curcode = modobj.code.now()
                elif self.editing[2] == 'hotp':
                    # if hotp, recalculate with the entered counter value
                    modobj.code = pyotp.hotp.HOTP(modobj.codestr)
                    modobj.curcode = modobj.code.at(self.ns_countersb.get_value())
            # if code hasn't been recalculated already,
            # and counter has changed, do this
            if self.editing[2] == 'hotp':
                if self.ns_countersb.get_value() != modobj.counter:
                    modobj.counter = int(self.ns_countersb.get_value())
                    modobj.curcode = modobj.code.at(modobj.counter)
            # change name and issuer if they're different
            modobj.name = self.ns_name_entry.get_text()
            modobj.issuer = self.ns_issuer_entry.get_text()
            # replace dict with new modified info
            self.codes[current_uuid] = modobj
            # update labels
            if self.editing[2] == 'totp':
                modobj.ui.authlbl.set_label(modobj.curcode)
            elif self.editing[2] == 'hotp':
                modobj.ui.authlbl.set_label(modobj.curcode)
                modobj.ui.counterlbl.set_label(modobj.counter.__str__())
            modobj.ui.issuerlbl.set_label(modobj.issuer)
            modobj.ui.namelbl.set_label(modobj.name)
            codeinfo = {
                'codetype': modobj.codetype,
                'name': modobj.name,
                'issuer': modobj.issuer,
                'secret': modobj.codestr,
                'pos': modobj.pos,
                'counter': modobj.counter if (modobj.codetype == 'hotp') else None,
                'uuid': current_uuid
            }
            # update database entry
            self.db_cursor.execute(f"""UPDATE authcodes SET type = '{modobj.codetype}',
                                    name = '{modobj.name}', issuer = '{modobj.issuer}',
                                    code = '{modobj.codestr}', position = '{modobj.pos}'
                                    WHERE uuid = '{current_uuid}'""")
            # update counter if the code is an hotp code
            if modobj.codetype == 'hotp':
                self.db_cursor.execute(f"UPDATE authcodes SET counter = '{modobj.counter}'")
            # commit database changes to disk
            threading.Thread(target=self._db_commit(), daemon=False)
            # clean up, and disable editing mode
            del modobj
            self.editing = [False, None, None]
            for x in self.codes:
                self.codes.get(x).ui.revealer.set_reveal_child(False)
            self.hb_editmode.set_active(False)
        # clear entry text for the next time it's accessed
        self.ns_secret_entry.set_text("")
        self.ns_name_entry.set_text("")
        self.ns_issuer_entry.set_text("")
        # clear preview avatar
        self.preview_avatar.set_image_load_func(self.avatar_load_blank)

    @staticmethod
    def validator(button=None, *data):
        if False in data:
            if button is not None:
                button.set_sensitive(False)
            return False
        else:
            if button is not None:
                button.set_sensitive(True)
            return True

    def hb_prefs_press(self, _):
        self.hb_lstack.set_visible_child_name("hbls_back")
        self.hb_rstack.set_visible_child_name("hbrs_noctl")
        self.main_stack.set_visible_child_name("ms_pref")

    def hb_back_press(self, widget):
        if self.main_stack.get_visible_child_name() == "ms_new":
            self.ns_cancel_press(widget)
            return
        self.main_stack.set_visible_child_name("ms_main_list_box")
        self.change_button_stack_state(True)

    def prefs_clear_data_click(self, _):
        self.change_button_stack_state(False)
        cd_dlg = Gtk.MessageDialog(buttons=Gtk.ButtonsType.YES_NO, modal=True, parent=self.application_window)
        cd_dlg.set_markup("<big>Warning</big>")
        cd_dlg.format_secondary_text("This cannot be reversed, and will delete your secrets.\n"
                                     "The program will exit when finished.\n"
                                     "Are you sure you want to continue?")
        cd_resp = cd_dlg.run()
        if cd_resp == Gtk.ResponseType.YES:
            try:
                cache_dir = GLib.get_user_data_dir()
                # Remove the database
                os.remove(f"{cache_dir}/authwallet.db")
                self.settings.set_value("obscure-secrets", GLib.Variant('b', True))
                self.settings.set_value("dark-theme", GLib.Variant('b', False))
                # Exit the program
                exit()
            except IOError:
                self.display_error("Could not remove all keys.\nThis could be a permissions error", log=False)
            cd_dlg.destroy()
        elif cd_resp == Gtk.ResponseType.NO:
            cd_dlg.destroy()
            self.hb_lstack.set_visible_child_name("hbls_back")

    def hb_editmode_press(self, widget):
        if widget.get_active():
            self.headerbar.get_style_context().add_class("headerbartheme")
            for x in self.codes:
                self.codes.get(x).ui.revealer.set_reveal_child(True)
            self.editmode = True
        else:
            for x in self.codes:
                self.codes.get(x).ui.revealer.set_reveal_child(False)
            self.editmode = False


    def copy_btn_press(self, widget, current_uuid):
        self.clipboard.set_text(self.codes.get(current_uuid).get_current_code(), -1)
        popover = Gtk.Popover()
        popover.set_relative_to(widget)
        plbl = Gtk.Label(label=f"Copied code for {self.codes.get(current_uuid).name} to the clipboard.")
        popover.add(plbl)
        popover.show_all()


    def del_btn_press(self, _, current_uuid):
        self.delete_code(current_uuid)

    """
        Remove a code from the list
    """
    def delete_code(self, current_uuid):
        # Confirm whether the user actually wants this
        cn_dlg = Gtk.MessageDialog(parent=self.application_window, modal=True, buttons=Gtk.ButtonsType.YES_NO)
        cn_dlg.set_markup('<big>Confirmation</big>')
        cn_dlg.format_secondary_text("Are you sure you want to remove this code?")
        cn_resp = cn_dlg.run()
        if cn_resp == Gtk.ResponseType.YES:
            cn_dlg.destroy()
            # Remove code from the UI
            self.codes.get(current_uuid).ui.row.destroy()
            # Destroy dict entry
            self.codes.pop(current_uuid)
            # Remove code with matching UUID from database
            self.db_cursor.execute(f"DELETE FROM authcodes where UUID = '{current_uuid}';")
            # Commit changes to the database
            threading.Thread(target=self._db_commit(), daemon=True)
            if len(self.codes) >= 1:
                self.hb_editmode.set_sensitive(True)
            else:
                self.editmode = False
                self.hb_editmode.set_active(False)
                self.hb_editmode.set_sensitive(False)
        else:
            cn_dlg.destroy()

    def edit_btn_press(self, _, current_uuid):
        self.change_button_stack_state(False)
        if self.codes.get(current_uuid).codetype == 'totp':
            self.editing = [True, current_uuid, 'totp']
            self.new_code_type = 'totp'
            self.newlistboxrow4.hide()
            self.ns_countersb.hide()
            self.ns_counterlbl.hide()
        elif self.codes.get(current_uuid).codetype == 'hotp':
            self.editing = [True, current_uuid, 'hotp']
            self.new_code_type = 'hotp'
            self.newlistboxrow4.show()
            self.ns_countersb.show()
            self.ns_counterlbl.show()
            self.ns_countersb.set_value(self.codes.get(current_uuid).counter)
        self.ns_name_entry.set_text(self.codes.get(current_uuid).name)
        self.ns_issuer_entry.set_text(self.codes.get(current_uuid).issuer)
        self.ns_secret_entry.set_text(self.codes.get(current_uuid).codestr)
        self.headerbar.set_show_close_button(False)
        self.hb_lstack.set_visible_child_name('hbls_back')
        self.hb_rstack.set_visible_child_name('hbrs_nexctl')
        self.main_stack.set_visible_child_name('ms_new')
        self.ns_add.set_label("Edit")

    def code_checker(self):
        interval = 30
        current = int(time() % 30)
        self.crf_progress.set_fraction(1-(current/interval))
        while True:
            if current < interval:
                current += 1
                self.crf_progress.set_fraction(1-(current/interval))
            elif interval == current:
                self.check_codes()
                self.crf_progress.set_fraction(1)
                current = 1
            sleep(1)


    def check_codes(self):
        if len(self.codes) > 0:
            for x in self.codes:
                if self.codes.get(x).codetype == 'totp':
                    totp_obj = self.codes.get(x).code
                    cur_code = self.codes.get(x).curcode
                    if totp_obj.verify(cur_code):
                        # code was ok, don't need to do anything
                        pass
                    else:
                        newcode = self.codes.get(x).get_current_code()
                        self.codes.get(x).curcode = newcode
                        self.codes.get(x).ui.authlbl.set_label(newcode)
                        self.mainlistbox.show_all()
                    del totp_obj, cur_code

    def prefs_dmslide_slide(self, _, state):
        if state:
            self.enable_dark_theme(True)
        else:
            self.enable_dark_theme(False)

    def ns_issue_change(self, entry_buffer=None, pos=None, chars=None, n_chars=None):
        self.issuer_ok = self.string_entry_buffer_handler(pos=pos, n_chars=n_chars,
                                                          buffer=entry_buffer)
        self.validator(self.ns_add, self.issuer_ok, self.name_ok, self.secret_ok)

    def ns_name_change(self, entry_buffer=None, pos=None, chars=None, n_chars=None):
        self.name_ok = self.string_entry_buffer_handler(pos=pos,  n_chars=n_chars,
                                                        buffer=entry_buffer)
        self.preview_avatar.set_text(entry_buffer.get_text())
        self.validator(self.ns_add, self.issuer_ok, self.name_ok, self.secret_ok)

    def ns_secret_change(self, entry_buffer=None, *_):
        try:
            self.ns_secret_entry.set_text(entry_buffer.get_text().upper())
        except TypeError:
            pass
        self.secret_ok = self.b32_checker(entry=self.ns_secret_entry,
                                          buffer=entry_buffer)
        self.validator(self.ns_add, self.issuer_ok, self.name_ok, self.secret_ok)

    def b32_checker(self, buffer=None, entry=None, *_):
        if not buffer.get_text() == "":
            try:
                if self.new_code_type == 'hotp':
                    test = pyotp.hotp.HOTP(buffer.get_text())
                    test.at(0)
                elif self.new_code_type == 'totp':
                    test = pyotp.totp.TOTP(buffer.get_text())
                    test.now()
                entry.get_style_context().remove_class("error")
                var = True
                return var
            except ValueError:
                entry.get_style_context().add_class("error")
                var = False
                return var
        else:
            entry.get_style_context().add_class("error")
            var = False
            return var

    @staticmethod
    def string_entry_buffer_handler(buffer=None, pos=None, n_chars=None):
        if not (buffer.get_text() == ""):
            try:
                if len(buffer.get_text()) > 20:
                    buffer.delete_text(pos, n_chars)
                var = True
                return var
            except ValueError:
                buffer.delete_text(pos, n_chars)
        else:
            var = False
            return var

    def newcode_enter_press(self, _widget) -> None:
        resp = self.validator(None, self.issuer_ok, self.name_ok, self.secret_ok)
        if resp:
            self.ns_add_code()
            self.main_stack.set_visible_child_name("ms_main_list_box")
            self.change_button_stack_state(True)
            self.headerbar.set_show_close_button(True)

    def increment_btn_press(self, _widget, current_uuid):
        self.increment_code(current_uuid)


    """
        Increment the counter of an hotp code
    """
    def increment_code(self, current_uuid):
        self.codes.get(current_uuid).counter += 1
        self.codes.get(current_uuid).ui.counterlbl.set_text(
            self.codes.get(current_uuid).counter.__str__()
            )
        self.codes.get(current_uuid).curcode = self.codes.get(current_uuid).code.at(
            int(self.codes.get(current_uuid).counter))
        self.codes.get(current_uuid).ui.authlbl.set_label(
            self.codes.get(current_uuid).curcode
            )
        self.db_cursor.execute(f"UPDATE authcodes SET counter = {self.codes.get(current_uuid).counter} WHERE uuid = '{current_uuid}'")
        threading.Thread(target=self._db_commit(), daemon=False)

    """
        Show the about dialog
    """
    def about_btn_press(self, _widget) -> None:
        self.aboutdialog.run()
        self.aboutdialog.hide()


    """
        Create a new list row and create an entry in the codes dict
    """
    def newlistrow(self, codeinfo) -> Gtk.ListBoxRow:

        # get the unique UUID of the key
        current_uuid = codeinfo['uuid']
        # get image data if it exists
        imagedata = codeinfo['image']
        # create the code object
        secret_obj = pyotp.totp.TOTP(codeinfo['secret']) if (codeinfo['codetype'] == 'totp') else pyotp.hotp.HOTP(codeinfo['secret'])
        secret = codeinfo['secret']
        if codeinfo['codetype'] == 'totp':
            authentication_code = secret_obj.now()
        elif codeinfo['codetype'] == 'hotp':
            authentication_code = secret_obj.at(codeinfo['counter'])
        # create a new row to work on, using the TwoFactorListBoxRow class
        # (listbox.py)
        new_row = TwoFactorListBoxRow(uuid=current_uuid)
        secret_name = codeinfo['name']
        secret_issuer = codeinfo['issuer']
        new_row.nameLabel.set_label(secret_name)
        new_row.issuerLabel.set_label(secret_issuer)
        new_row.authCodeLabel.set_label(authentication_code)
        new_row.copyButton.connect("clicked", self.copy_btn_press, current_uuid)
        new_row.deleteButton.connect("clicked", self.del_btn_press, current_uuid)
        new_row.editButton.connect("clicked", self.edit_btn_press, current_uuid)
        new_row.avatar.set_text(secret_name)
        if imagedata is not None:
            image = GLib.Bytes.new(GLib.base64_decode(imagedata))
            loader = GdkPixbuf.PixbufLoader.new()
            loader.write_bytes(image)
            pixbuf = loader.get_pixbuf()
            loader.close()
            # get scaling factor of window
            scale_factor = self.application_window.get_scale_factor()
            # get size of avatar
            avatar_size = new_row.avatar.get_size()
            # adjust avatar size by multiplying it by scale factor
            avatar_size *= scale_factor
            # scale pixbuf to avatar size
            #scaled_pixbuf = pixbuf.scale_simple(avatar_size, avatar_size,
            #                                    GdkPixbuf.InterpType.BILINEAR)
            #del pixbuf
            new_row.avatar.set_image_load_func(self.avatar_load_func, pixbuf)
        # add authentication button to sizegroup
        self.authentication_sizegroup.add_widget(new_row.copyButton)
        if codeinfo['codetype'] == 'totp':
            # we don't need this for a totp code, might as well get rid of it to save memory
            new_row.incrementCounterButton.destroy()
            new_row.seperator.destroy()
        elif codeinfo['codetype'] == 'hotp':
            #self.increment_sizegroup.add_widget(new_row.incrementCounterButton)
            new_row.incrementCounterButton.connect("clicked", self.increment_btn_press, current_uuid)
            new_row.incrementCounterLabel.set_text(f"{codeinfo['counter'].__str__()}")
        # get position, for re-ordering later
        pos = codeinfo['pos']
        # pack everything into the TwoFactorCode class
        codeobj = TwoFactorCode(
            name = secret_name,
            issuer = secret_issuer,
            codetype = codeinfo['codetype'],
            codestr = secret,
            counter = codeinfo['counter'] if (codeinfo['codetype'] == 'hotp') else None,
            pos = pos,
            imagedata = imagedata,
            ui = TwoFactorUIElements(
                revealer = new_row.revealer,
                authlbl = new_row.authCodeLabel,
                issuerlbl = new_row.issuerLabel,
                namelbl = new_row.nameLabel,
                row = new_row.row,
                avatar = new_row.avatar,
                mainlayout = new_row.mainLayout,
                counterlbl = new_row.incrementCounterLabel if (codeinfo['codetype'] == 'hotp') else None
                )
            )
        if codeinfo['codetype'] == 'hotp':
            # if the code is an hotp code, set the counter label
            codeobj.ui.counterlbl.set_label(codeinfo['counter'].__str__())
        self.codes[current_uuid] = codeobj
        # set up drag'n'drop

        # make each list row a target for drag'n'drop

        new_row.handle.drag_source_set(Gdk.ModifierType.BUTTON1_MASK,
                                          [self.targetEntry],
                                          Gdk.DragAction.MOVE)


        # handle connections
        new_row.handle.connect("drag-data-get", self.drag_data_get, new_row)
        new_row.handle.connect("drag-begin", self.drag_begin, new_row.infoLayout)
        new_row.handle.connect("drag-failed", self.drag_end_or_fail)
        #new_row.row.drag_dest_set(Gtk.DestDefaults.MOTION,
        #                 [self.targetEntry],
        #                 Gdk.DragAction.MOVE)
        # add borders
        new_row.row.get_style_context().add_class("crborder")
        return new_row
        if self.editmode:
            new_row.revealer.set_reveal_child(True)
        return new_row

    """
        Enable secret obscuration when the slider is active
    """
    def prefs_hiddensecret_slide(self, widget, active) -> None:
        if active:
            # set the obscure-secrets gsetting to true, and make chars invisible in the ns_secret_entry box
            self.settings.set_value("obscure-secrets", GLib.Variant('b', True))
            self.ns_secret_entry.set_visibility(False)
        elif not active:
            self.settings.set_value("obscure-secrets", GLib.Variant('b', False))
            self.ns_secret_entry.set_visibility(True)

    """
        Import codes from an authenticator backup
        Only works with unencrypted Aegis authenticator backups as of now.
    """
    def import_code(self, widget):
        chooser = Gtk.FileChooserDialog(
            title="Import Backup",
            parent=self.application_window,
            action=Gtk.FileChooserAction.OPEN
        )
        chooser.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN,
            Gtk.ResponseType.OK
        )
        response = chooser.run()
        if response == Gtk.ResponseType.OK:
            filename = chooser.get_filename()
            # destroy file dialog
            chooser.destroy()
            # enable the spinner
            self.spinner.start()
            # launch a thread to read aegis json
            threading.Thread(target=self._read_aegis_json(filename), daemon=False).start()

    """
        Import codes from Aegis authenticator JSON
    """
    def _read_aegis_json(self, filename):
        file = open(filename, "r")
        jsondata = json.load(file)
        file.close()
        for x in jsondata["db"]["entries"]:
            item = x
            # if code is a recognized type
            if item['type'] == 'totp' or item['type'] == 'hotp':
                cdict = {
                    'codetype': item['type'],
                    'name': item['name'],
                    'issuer': item['issuer'],
                    'secret': item['info']['secret'],
                    'pos': len(self.codes)+1,
                    'uuid': uuid4().__str__(),
                    'image':  item['icon'],
                    'counter': item['info']['counter'] if (item['type'] == 'hotp') else None
                }
                self.mainlistbox.add(
                    self.newlistrow(cdict)
                )
                self.db_cursor.execute(f"""INSERT INTO authcodes (uuid, name, type, issuer, position, code, image)
                                          VALUES ('{uuid4().__str__()}', '{item['name']}', '{item['type']}', '{item['issuer']}', '{len(self.codes)+1}', '{item['info']['secret']}', '{item['icon']}')""")
            else:
                pass
        # Commit database changes to the disk
        threading.Thread(target=self._db_commit(), daemon=False).start()
        # Move back to the main view
        self.main_stack.set_visible_child_name("ms_main_list_box")
        self.change_button_stack_state(True)
        self.spinner.stop()
        self.spinner.hide()

    def avatar_load_func(self, size, pixbuf):
        scaled_pixbuf = pixbuf.scale_simple(size,
                                            size,
                                            GdkPixbuf.InterpType.BILINEAR)
        return scaled_pixbuf

    # provide nothing to the avatar, in effect resetting it to using initials
    def avatar_load_blank(self, size):
        return None

    def choose_image(self, *data) -> GdkPixbuf.Pixbuf:
        imagepath = self.get_image_path()
        # imagepath returns false if loading is cancelled
        if imagepath is not False:
            avatarsize = self.preview_avatar.get_size()
            avatarsize *= self.application_window.get_scale_factor()
            self.currentpixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(imagepath,
                                                                        avatarsize,
                                                                        avatarsize)
            self.preview_avatar.set_image_load_func(self.avatar_load_func,
                                                    self.currentpixbuf)
            self.hasimage = True
            self.imagepath = imagepath
            self.clear_image_btn_revealer.set_reveal_child(True)
        else:
            return

    def clear_image(self, *data):
        self.preview_avatar.set_image_load_func(self.avatar_load_blank)
        self.clear_image_btn_revealer.set_reveal_child(False)
        self.hasimage = False

    def get_image_path(self) -> str :
        # define valid image types, as the latter part of the mimetype
        valid_mime_types = ["jpeg", "png"]
        # create a file dialog
        dialog = Gtk.FileChooserDialog(
            title="Choose a picture",
            action=Gtk.FileChooserAction.OPEN,
            modal=True,
            parent=self.application_window
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN,
            Gtk.ResponseType.OK
        )
        # create filters for dialog
        filefilter_images = Gtk.FileFilter()
        filefilter_all = Gtk.FileFilter()
        filefilter_images.set_name("Images")
        filefilter_all.set_name("All Filetypes")
        # add a list of image mimetypes to the image filter
        for mimetype in valid_mime_types:
            filefilter_images.add_mime_type(f"image/{mimetype}")
        # don't filter any files with the all filter
        filefilter_all.add_pattern("*")
        dialog.add_filter(filefilter_images)
        dialog.add_filter(filefilter_all)
        dlgresponse = dialog.run()
        if dlgresponse == Gtk.ResponseType.OK:
            imagepath = dialog.get_filename()
            dialog.destroy()
            return imagepath
        elif dlgresponse == Gtk.ResponseType.CANCEL:
            dialog.destroy()
            return False

    def drag_data_get(self, widget, context, selection, info, timestamp, row):
        # add the rows' index to the selection data
        selection.set(selection.get_target(), 8, b'%d' % (row.get_index(),))


    # TODO: copy this to ::drag-move signal, so that it can update the highlight
    def drag_data_recieved(self, widget, context, x, y, data, info, time):
        #self.move_widgets(int(data.get_data().decode()), widget.get_index())
        # TODO: handle NoneType for row_at_y, as end of list drop, and highlight accordingly
        alloc = widget.get_allocation()
        original_index = data.get_data().decode()
        row = self.mainlistbox.get_row_at_y(y)
        if row is not None:
            row_alloc = row.get_allocation()
            row_ub = row_alloc.y
            row_lb = row_alloc.y + row_alloc.height
            row_hwp = (row_lb + row_ub) / 2
            drop_on_top_half = True if (y <= row_hwp) else False
            target_index = row.get_index() if (drop_on_top_half) else row.get_index()
        else:
            target_index = len(self.mainlistbox)
        if target_index != original_index:
            self.spinner.start()
            #GLib.timeout_add_seconds (0, self.move_row, original_index, target_index)
            self.move_row(original_index, target_index)
        self.drag_end_or_fail()
        # TODO: work out using y where on the listbox we are, and draw using other connectors

    def drag_motion(self, widget, context, x, y, time):
        # TODO: this really isn't very efficient
        for x in self.codes:
            self.codes.get(x).ui.row.get_style_context().remove_class("tophighlight")
            self.codes.get(x).ui.row.get_style_context().remove_class("bottomhighlight")
            self.codes.get(x).ui.row.get_style_context().add_class("crborder")
        row = self.mainlistbox.get_row_at_y(y)
        if row is not None:
            row_alloc = row.get_allocation()
            row_ub = row_alloc.y
            row_lb = row_alloc.y + row_alloc.height
            row_hwp = (row_lb + row_ub) / 2
            on_top_half = True if (y < row_hwp) else False
            if on_top_half:
                row.get_style_context().remove_class("crborder")
                row.get_style_context().remove_class("bottomhighlight")
                row.get_style_context().add_class("tophighlight")
            else:
                row.get_style_context().remove_class("crborder")
                row.get_style_context().remove_class("tophighlight")
                row.get_style_context().add_class("bottomhighlight")
        else:
            row = self.mainlistbox.get_row_at_index(len(self.mainlistbox)-1)
            row.get_style_context().remove_class("crborder")
            row.get_style_context().remove_class("tophighlight")
            row.get_style_context().add_class("bottomhighlight")
            pass
        # TODO: scrolling logic
        return
        scroll_adjustment = self.listbox_scrolledwindow.get_vadjustment()
        listbox_alloc = self.mainlistbox.get_allocation()
        hotzone = 24
        b_hotzone = listbox_alloc.height - hotzone
        print(scroll_adjustment.get_value())
        print(scroll_adjustment.get_upper())
        if y < hotzone:
            print(self.listbox_scrolledwindow.get_vadjustment())
            # scroll up
        if y >= b_hotzone:
            print("SCROLLDOWN")
            # scroll down

    def drag_begin(self, widget, context, preview_widget):
        # hide ctrl strip when dragging, so that more items can be present at once
        self.hb_editmode.set_sensitive(False)
        for x in self.codes:
            self.codes.get(x).ui.revealer.set_reveal_child(False)
        # add a temporary background-color & border to the preview box
        preview_widget.get_style_context().add_class("preview_box")
        # create a cairo representation of the row when dragging
        preview_alloc = preview_widget.get_allocation()
        cairo_surface = cairo.ImageSurface(cairo.Format.ARGB32,
                                           preview_alloc.width,
                                           preview_alloc.height)
        cairo_context = cairo.Context(cairo_surface)
        preview_widget.draw(cairo_context)
        Gtk.drag_set_icon_surface(context, cairo_surface)
        # remove temporary style class
        preview_widget.get_style_context().remove_class("preview_box")
        del preview_alloc
        del cairo_surface
        del cairo_context
        # start a timer that handles list scrolling
        # TODO: the timer that handles list scrolling

    """
        clean up from drag operation
    """
    def drag_end_or_fail(self, *data):
        # make editmode button sensitive again
        self.hb_editmode.set_sensitive(True)
        # show ctrl strip again when drag ends
        for x in self.codes:
            self.codes.get(x).ui.revealer.set_reveal_child(True)
            self.codes.get(x).ui.row.get_style_context().remove_class("tophighlight")
            self.codes.get(x).ui.row.get_style_context().remove_class("bottomhighlight")
            self.codes.get(x).ui.row.get_style_context().add_class("crborder")

    """
        moves a row to a new location
    """
    def move_row(self, src, dest):
        event = threading.Event()
        src_uuid = self.mainlistbox.get_row_at_index(int(src)).uuid
        dest_uuid = uuid4().__str__()
        oldObj = self.codes.get(src_uuid)
        self.mainlistbox.remove(self.codes.get(src_uuid).ui.row)
        self.mainlistbox.insert(self.codes.get(src_uuid).ui.row, dest)
        threading.Thread(target=self.update_positions(), daemon=False)

    """
        updates the position of codes
    """
    def update_positions(self):
        for x in self.codes:
            # update position for code
            self.codes.get(x).pos = self.codes.get(x).ui.row.get_index() + 1
            # update position in database
            self.db_cursor.execute(f"UPDATE authcodes SET position = '{self.codes.get(x).pos}' WHERE UUID='{self.codes.get(x).uuid}'")
        threading.Thread(target=self._db_commit(), daemon=False)

application = MainApplication()
application.application_window.show()
Gtk.main()
