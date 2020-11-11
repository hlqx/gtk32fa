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
from gi.repository import Gtk, Gio, Gdk, GLib
import pyotp
import threading
import yaml
import base64
import hashlib
import pathlib
import os
import html
import secretstorage
import json
#import pyzbar.pyzbar
# TODO: add to flatpak manifest
from time import time
from uuid import uuid4
from operator import itemgetter
from cryptography.fernet import Fernet, InvalidToken
from time import sleep
from io import StringIO
from .listbox import TwoFactorListBoxRow, EmptyListWidget
from .twofactorcode import TwoFactorCode, TwoFactorUIElements
from .screenshot import GNOMEScreenshot
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GObject, GLib, Gio


class MainApplication(Gtk.Application):

    def __init__(self):
        super().__init__(application_id='com.niallasher.twofactor',
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.gtkbuilder = Gtk.Builder()
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
        self.qrbtn = self.gtkbuilder.get_object("btn_qrimport")
        self.import_code_btn.connect("clicked", self.import_code)
        self.crf_progress.set_fraction(1)
        self.mainlistbox.get_style_context().add_class("codelistbox")
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
            "btn_importcodes_clicked": self.import_code
        }
        self.qrbtn.connect('clicked', self.qr_import)
        # other things
        self.darktheme = False
        self.file_data = StringIO()
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
        # create a gtksettings object, to allow changing dark theme later
        self.gtksettings = Gtk.Settings().get_default()
        css_provider = Gtk.CssProvider()
        css_provider.load_from_resource("com/niallasher/twofactor/stylesheet.css")
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),
                                                 css_provider,
                                                 Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        code_validator = threading.Thread(target=self.code_checker,
                                          daemon=True)
        code_validator.start()
        # set placeholder widget for the main list box
        self.mainlistbox.set_placeholder(EmptyListWidget())
        # create settings object
        self.settings = Gio.Settings.new("com.niallasher.twofactor")
        dbus_connection = secretstorage.dbus_init()
        self.secret_collection = secretstorage.get_default_collection(dbus_connection)
        self.load_config()
        self.import_storage()
        Gtk.Window.__init__(self.application_window)
        #self.main_stack.set_visible_child_name("ms_import_types")
        #self.import_types_list_box = self.gtkbuilder.get_object("import_types_list_box")

    def load_config(self):
        if self.settings.get_value('dark-theme').unpack():
            self.enable_dark_theme(True)
        else:
            self.enable_dark_theme(False)
        if self.settings.get_value('obscure-secrets').unpack():
            self.prefs_hiddensecret.set_active(True)
            self.ns_secret_entry.set_visibility(False)

    def enable_all_button_stacks(self, y=True):
        if y:
            self.hb_lstack.set_visible_child_name("hbls_gctl")
            self.hb_rstack.set_visible_child_name("hbrs_gctl")
        elif not y:
            self.hb_lstack.set_visible_child_name("hbls_noctl")
            self.hb_rstack.set_visible_child_name("hbrs_noctl")
        if len(self.codes) >= 1:
            self.hb_editmode.set_sensitive(True)
        else:
            self.hb_editmode.set_sensitive(False)

    def import_storage(self):
        yamldata = []
        if self.secret_collection.is_locked():
            self.secret_collection.unlock()
        secrets = self.secret_collection.search_items({"application": "com.niallasher.twofactor"})
        for secret in secrets:
            data = secret.get_secret()
            uuid = secret.get_attributes()['uuid']
            data_decoded = GLib.base64_decode(data.decode("utf-8"))
            info = yaml.safe_load(data_decoded)
            info['uuid'] = uuid
            yamldata.append(info)
        if len(yamldata) != 0:
            # sort the dict entries by position, to allow for restoring sorting
            yamldata.sort(key=itemgetter("pos"))
            for item in yamldata:
                if item['codetype'] == 'totp':
                    self.mainlistbox.add(
                        self.newlistrow({
                            'codetype': item['codetype'],
                            'name': item['name'],
                            'issuer': item['issuer'],
                            'secret': item['secret'],
                            'pos': item['pos'],
                            'uuid': item['uuid']
                            }
                        )
                    )
                else:
                    self.mainlistbox.add(
                        self.newlistrow({
                            'codetype': item['codetype'],
                            'name': item['name'],
                            'issuer': item['issuer'],
                            'secret': item['secret'],
                            'pos': item['pos'],
                            'counter': item['counter'].__int__(),
                            'uuid': item['uuid']
                            }
                        )
                    )
        if len(self.codes) >= 1:
            self.hb_editmode.set_sensitive(True)

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
        self.new_code_generic()

    def new_code_totp(self, _):
        self.new_code_type = "totp"
        self.ns_hide_counter_options(True)
        self.new_code_generic()

    def new_code_generic(self):
        self.an_pop.hide()
        self.enable_all_button_stacks(False)
        self.hb_lstack.set_visible_child_name("hbls_back")
        self.headerbar.set_show_close_button(False)
        self.hb_rstack.set_visible_child_name("hbrs_nexctl")
        self.main_stack.set_visible_child_name("ms_new")

    def ns_hide_counter_options(self, y=True):
        if y:
            self.ns_counterlbl.hide()
            self.ns_countersb.hide()
        elif not y:
            self.ns_countersb.show()
            self.ns_counterlbl.show()

    def ns_cancel_press(self, _):
        self.headerbar.set_show_close_button(True)
        self.enable_all_button_stacks(True)
        self.main_stack.set_visible_child_name("ms_main_list_box")
        self.ns_hide_counter_options(False)
        if True in self.editing:
            self.editing = [False, None, None]
        if self.new_code_type == 'hotp':
            self.ns_countersb.set_value(0)
        for x in self.codes:
            self.codes.get(x).ui.stack.set_visible_child_name('s1')
        self.hb_editmode.set_active(False)
        self.new_code_type = None
        self.ns_secret_entry.set_text("")
        self.ns_name_entry.set_text("")
        self.ns_issuer_entry.set_text("")
        self.ns_add.set_label("Add")

    def ns_add_press(self, _):
        self.headerbar.set_show_close_button(True)
        self.ns_add_code()
        self.main_stack.set_visible_child_name("ms_main_list_box")
        self.enable_all_button_stacks(True)
        self.ns_add.set_label("Add")

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
            codeinfo = {
                'codetype': self.new_code_type,
                'name': secret_name,
                'issuer': secret_issuer,
                'secret': secret_plaintext,
                'pos': len(self.codes) + 1,
                'counter': self.ns_countersb.get_value().__int__() if (self.new_code_type == 'hotp') else None,
                'uuid': uuid
            }
            self.mainlistbox.add(self.newlistrow(codeinfo))
            self.mainlistbox.show_all()
            self.secret_collection.create_item(
                f'{secret_name} ({secret_issuer})',
                {
                    "application": "com.niallasher.twofactor",
                    "uuid": uuid
                },
                GLib.base64_encode(yaml.safe_dump(codeinfo).encode('utf-8'))
            )
        elif True in self.editing:
            current_uuid = self.editing[1]
            modobj = self.codes.get(current_uuid)
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
            # update yaml
            codeinfo = {
                'codetype': modobj.codetype,
                'name': modobj.name,
                'issuer': modobj.issuer,
                'secret': modobj.codestr,
                'pos': modobj.pos,
                'counter': modobj.counter if (modobj.codetype == 'hotp') else None,
                'uuid': current_uuid
            }
            self.secret_collection.create_item(
                f'{codeinfo["name"]} ({codeinfo["issuer"]})',
                {'application': 'com.niallasher.twofactor', 'uuid': current_uuid},
                GLib.base64_encode(yaml.safe_dump(codeinfo).encode('utf-8')),
                replace=True
            )
            # clean up, and disable editing mode
            del modobj
            self.editing = [False, None, None]
            for x in self.codes:
                self.codes.get(x).ui.stack.set_visible_child_name('s1')
            self.hb_editmode.set_active(False)
        # clear entry text for the next time it's accessed
        self.ns_secret_entry.set_text("")
        self.ns_name_entry.set_text("")
        self.ns_issuer_entry.set_text("")

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
        self.enable_all_button_stacks(True)

    def prefs_clear_data_click(self, _):
        self.enable_all_button_stacks(False)
        cd_dlg = Gtk.MessageDialog(buttons=Gtk.ButtonsType.YES_NO, modal=True, parent=self.application_window)
        cd_dlg.set_markup("<big>Warning</big>")
        cd_dlg.format_secondary_text("This cannot be reversed, and will delete your secrets.\n"
                                     "The program will exit when finished.\n"
                                     "Are you sure you want to continue?")
        cd_resp = cd_dlg.run()
        if cd_resp == Gtk.ResponseType.YES:
            try:
                searchresults = self.secret_collection.search_items({'application': 'com.niallasher.twofactor'})
                for x in searchresults:
                    x.delete()
            except:
                err_dlg = Gtk.MessageDialog(buttons=Gtk.ButtonsType.OK,
                modal=True,
                parent=self.application_window)
                err_dlg.set_markup("<big>Error</big>")
                err_dlg.format_secondary_text("Could not remove all keys.\n"
                                              "This could be a permissions error.")
            cd_dlg.destroy()
            exit()
        elif cd_resp == Gtk.ResponseType.NO:
            cd_dlg.destroy()
            self.hb_lstack.set_visible_child_name("hbls_back")

    def hb_editmode_press(self, widget):
        if widget.get_active():
            self.headerbar.get_style_context().add_class("suggested-action")
            for x in self.codes:
                self.codes.get(x).ui.stack.set_visible_child_name('s2')
            self.editmode = True
        else:
            for x in self.codes:
                self.codes.get(x).ui.stack.set_visible_child_name('s1')
            self.editmode = False

    def copy_btn_press(self, widget, current_uuid):
        self.clipboard.set_text(self.codes.get(current_uuid).get_current_code(), -1)
        popover = Gtk.Popover()
        popover.set_relative_to(widget)
        plbl = Gtk.Label(label=f"Copied code for {self.codes.get(current_uuid).name} to the clipboard.")
        popover.add(plbl)
        popover.show_all()

    def del_btn_press(self, _, current_uuid):
        cn_dlg = Gtk.MessageDialog(parent=self.application_window, modal=True, buttons=Gtk.ButtonsType.YES_NO)
        cn_dlg.set_markup('<big>Confirmation</big>')
        cn_dlg.format_secondary_text("Are you sure you want to remove this code?")
        cn_resp = cn_dlg.run()
        if cn_resp == Gtk.ResponseType.YES:
            cn_dlg.destroy()
            self.codes.get(current_uuid).ui.row.destroy()
            self.codes.pop(current_uuid)
            searchresults = self.secret_collection.search_items({'application': 'com.niallasher.twofactor', 'uuid': current_uuid})
            for x in searchresults:
                x.delete()
            if len(self.codes) >= 1:
                self.hb_editmode.set_sensitive(True)
            else:
                self.editmode = False
                self.hb_editmode.set_active(False)
                self.hb_editmode.set_sensitive(False)
        else:
            cn_dlg.destroy()

    def edit_btn_press(self, _, current_uuid):
        self.enable_all_button_stacks(False)
        if self.codes.get(current_uuid).codetype == 'totp':
            self.editing = [True, current_uuid, 'totp']
            self.new_code_type = 'totp'
            self.ns_countersb.hide()
            self.ns_counterlbl.hide()
        elif self.codes.get(current_uuid).codetype == 'hotp':
            self.editing = [True, current_uuid, 'hotp']
            self.new_code_type = 'hotp'
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

    def move_list_item(self, _, current_uuid, up):
        current_index = self.codes.get(current_uuid).ui.row.get_index()
        if up:
            # if the list is inserted at -1, it will show up at the end, which we don't want
            # on second thought, maybe we do idk
            # anyway prevent it for now
            if current_index == 0:
                # break out if first on list and moving up
                return
        new_index = current_index - 1 if up else current_index + 1
        box = Gtk.ListBoxRow()
        self.codes.get(current_uuid).ui.row.remove(self.codes.get(current_uuid).ui.rowhbox)
        self.codes.get(current_uuid).ui.row.destroy()
        self.codes.get(current_uuid).ui.row = box
        box.add(self.codes.get(current_uuid).ui.rowhbox)
        self.mainlistbox.insert(self.codes.get(current_uuid).ui.row, new_index)
        self.mainlistbox.show_all()
        del box, new_index, current_index
        # index counting starts from one in the storage, so add one
        # to the current index of the listbox, and add it to the data storage
        # we have to regen the whole list to prevent conflicts
        for x in self.codes:
            self.codes.get(x).pos = self.codes.get(x).ui.row.get_index() + 1
        self.update_all_key_entries()

    def update_all_key_entries(self):
        searchresults = self.secret_collection.search_items({'application': 'com.niallasher.twofactor'})
        for x in searchresults:
            working_uuid = x.get_attributes()['uuid']
            secret = yaml.safe_load(GLib.base64_decode(x.get_secret().decode("utf-8")))
            secret['pos'] = self.codes.get(working_uuid).pos
            x.set_secret(base64.urlsafe_b64encode(yaml.safe_dump(secret).encode('utf-8')))

    def newcode_enter_press(self, _):
        resp = self.validator(None, self.issuer_ok, self.name_ok, self.secret_ok)
        if resp:
            self.ns_add_code()
            self.main_stack.set_visible_child_name("ms_main_list_box")
            self.enable_all_button_stacks(True)
            self.headerbar.set_show_close_button(True)

    def increment_btn_press(self, _, current_uuid):
        self.codes.get(current_uuid).counter += 1
        self.codes.get(current_uuid).ui.counterlbl.set_text(
            self.codes.get(current_uuid).counter.__str__()
            )
        self.codes.get(current_uuid).curcode = self.codes.get(current_uuid).code.at(
            int(self.codes.get(current_uuid).counter))
        self.codes.get(current_uuid).ui.authlbl.set_label(
            self.codes.get(current_uuid).curcode
            )
        searchresults = self.secret_collection.search_items({'application': 'com.niallasher.twofactor', 'uuid': current_uuid})
        for x in searchresults:
            secret = yaml.safe_load(GLib.base64_decode(x.get_secret().decode("utf-8")))
            secret['counter'] = self.codes.get(current_uuid).counter
            x.set_secret(GLib.base64_encode(yaml.safe_dump(secret).encode('utf-8')))

    def about_btn_press(self, _):
        self.aboutdialog.run()
        self.aboutdialog.hide()

    def newlistrow(self, codeinfo):
        # get the unique UUID of the key
        current_uuid = codeinfo['uuid']
        # create the code object
        secret_obj = pyotp.totp.TOTP(codeinfo['secret']) if (codeinfo['codetype'] == 'totp') else pyotp.hotp.HOTP(codeinfo['secret'])
        secret = codeinfo['secret']
        if codeinfo['codetype'] == 'totp':
            authentication_code = secret_obj.now()
        elif codeinfo['codetype'] == 'hotp':
            authentication_code = secret_obj.at(codeinfo['counter'])
        # create a new row to work on, using the TwoFactorListBoxRow class
        # (listbox.py)
        new_row = TwoFactorListBoxRow()
        secret_name = codeinfo['name']
        secret_issuer = codeinfo['issuer']
        new_row.name_label.set_label(secret_name)
        new_row.issuer_label.set_label(secret_issuer)
        new_row.authentication_code_label.set_label(authentication_code)
        new_row.copy_button.connect("clicked", self.copy_btn_press, current_uuid)
        new_row.delete_button.connect("clicked", self.del_btn_press, current_uuid)
        new_row.edit_button.connect("clicked", self.edit_btn_press, current_uuid)
        new_row.move_up_button.connect("clicked", self.move_list_item, current_uuid, True)
        new_row.move_down_button.connect("clicked", self.move_list_item, current_uuid, False)
        # add authentication button to sizegroup
        self.authentication_sizegroup.add_widget(new_row.copy_button)
        if codeinfo['codetype'] == 'totp':
            # we don't need this for a totp code, might as well get rid of it to save memory
            new_row.increment_counter_button.destroy()
        elif codeinfo['codetype'] == 'hotp':
            #self.increment_sizegroup.add_widget(new_row.increment_counter_button)
            new_row.increment_counter_button.connect("clicked", self.increment_btn_press, current_uuid)
            new_row.counter_label.set_text(f"{codeinfo['counter'].__str__()}")
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
            ui = TwoFactorUIElements(
                stack = new_row.stack,
                authlbl = new_row.authentication_code_label,
                issuerlbl = new_row.issuer_label,
                namelbl = new_row.name_label,
                row = new_row.row,
                rowhbox = new_row.row_hbox,
                counterlbl = new_row.counter_label if (codeinfo['codetype'] == 'hotp') else None
                )
            )
        if codeinfo['codetype'] == 'hotp':
            # if the code is an hotp code, set the counter label
            codeobj.ui.counterlbl.set_label(codeinfo['counter'].__str__())
        self.codes[current_uuid] = codeobj
        return new_row
        if self.editmode:
            new_row.stack.get_child_by_name("s2").show_all()
            new_row.stack.set_visible_child_name("s2")
        return new_row

    def prefs_hiddensecret_slide(self, widget, active):
        if active:
            # set the obscure-secrets gsetting to true, and make chars invisible in the ns_secret_entry box
            self.settings.set_value("obscure-secrets", GLib.Variant('b', True))
            self.ns_secret_entry.set_visibility(False)
        elif not active:
            self.settings.set_value("obscure-secrets", GLib.Variant('b', False))
            self.ns_secret_entry.set_visibility(True)

    def import_code(self, widget):
        # import an unencrypted aegis authenticator backup
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
            file = open(chooser.get_filename(), "r")
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
                        'counter': item['info']['counter'] if (item['type'] == 'hotp') else None
                    }
                    self.mainlistbox.add(
                        self.newlistrow(cdict)
                    )
                    self.secret_collection.create_item(
                    f'{item["name"]} ({item["issuer"]})',
                    {
                        "application": "com.niallasher.twofactor",
                        "uuid": cdict['uuid']
                    },
                    GLib.base64_encode(yaml.safe_dump(cdict).encode('utf-8')))
                else:
                    pass
            # move back to the main view
            self.main_stack.set_visible_child_name("ms_main_list_box")
            self.enable_all_button_stacks(True)
        chooser.destroy()

    def qr_import(self, *data):
        print(data)
        print("import not implemented")

application = MainApplication()
application.application_window.show()
Gtk.main()
