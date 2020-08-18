#!/usr/bin/env python3
import gi
import pyotp as otp
import threading, yaml, base64, hashlib
from cryptography.fernet import Fernet
from xdg import XDG_DATA_HOME, XDG_CONFIG_HOME
from pathlib import Path
from os import path, mkdir, urandom
from time import sleep
from io import StringIO
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

class MainWindow(Gtk.Window):
    def __init__(self):
        # self.settings for theme
        self.settings = Gtk.Settings.get_default()
        self.codelist = []
        self.rowlist = []
        Gtk.Window.__init__(self)
        # set up window parameters
        self.set_title("GTK32FA")
        self.set_default_size(640, 640)
        # make a headerbar for the window
        headerbar = Gtk.HeaderBar(title="GTK32FA", show_close_button=True)
        self.set_titlebar(headerbar)
        # headerbar buttons
        self.headerbarbtn_addcode = Gtk.Button.new_from_icon_name("list-add", Gtk.IconSize.BUTTON)
        self.headerbarbtn_darkmode = Gtk.Button.new_from_icon_name("weather-clear-night", Gtk.IconSize.BUTTON)
        self.headerbarbtn_editmode = Gtk.ToggleButton(label="Edit", sensitive=False)
        headerbar.pack_start(self.headerbarbtn_addcode)
        headerbar.pack_start(self.headerbarbtn_editmode)
        headerbar.pack_end(self.headerbarbtn_darkmode)
        # connect window close to window fucking dying
        self.connect("destroy", Gtk.main_quit)
        # stack control, make it main widget for window
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.add(self.stack)
        # make a scrolledwindow component
        codeview_scolledwindow = Gtk.ScrolledWindow()
        # list view test
        self.codeviewbox = Gtk.ListBox()
        self.codeviewbox.set_selection_mode(Gtk.SelectionMode.NONE)
        # add the codeview to the scrolledwindow
        codeview_scolledwindow.add(self.codeviewbox)
        # connect new button to it's function
        self.headerbarbtn_darkmode.connect("clicked", self.darkmode_clicked  )
        self.headerbarbtn_addcode.connect("clicked", self.newcode_clicked, self.codeviewbox)
        self.headerbarbtn_editmode.connect("clicked", self.editmode_clicked)
        code_validation_thread = threading.Thread(target=self.code_checker, daemon=True)
        code_validation_thread.start()
        # # # # # # # # # 
        # new code page #
        # # # # # # # # #
        newcode_layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        newcode_layout_horizontal = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        newcode_layout_spacing_h = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        newcode_layout_spacing_v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        newcode_layout_labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, homogeneous=True)
        newcode_layout_entries = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        newcode_buttonbox = Gtk.ButtonBox(orientation=Gtk.Orientation.HORIZONTAL, layout_style=Gtk.ButtonBoxStyle.EXPAND, spacing=0)
        newcode_name_label = Gtk.Label(label="Name:", xalign=0)
        newcode_issuer_label = Gtk.Label(label="Issuer:", xalign=0)
        newcode_secret_label = Gtk.Label(label="Secret:", xalign=0)
        newcode_cancel_button = Gtk.Button(label="Cancel")
        self.newcode_add_button = Gtk.Button(label="Add", sensitive=False)
        self.newcode_add_button.get_style_context().add_class("suggested-action")
        newcode_cancel_button.get_style_context().add_class("destructive-action")
        self.newcode_name_buffer = Gtk.EntryBuffer()
        self.newcode_issuer_buffer = Gtk.EntryBuffer()
        self.newcode_secret_buffer = Gtk.EntryBuffer()
        self.newcode_name_entry = Gtk.Entry(buffer=self.newcode_name_buffer)
        self.newcode_issuer_entry = Gtk.Entry(buffer=self.newcode_issuer_buffer)
        self.newcode_secret_entry = Gtk.Entry(buffer=self.newcode_secret_buffer)
        # pack things
        newcode_layout_spacing_v.set_center_widget(newcode_layout_spacing_h)
        newcode_layout_spacing_h.set_center_widget(newcode_layout)
        newcode_layout.pack_start(newcode_layout_horizontal, True, True, 6)
        newcode_layout.pack_end(newcode_buttonbox, True, False, 6)
        newcode_buttonbox.pack_start(newcode_cancel_button, True, True, 0)
        newcode_buttonbox.pack_end(self.newcode_add_button, True, True, 0)
        newcode_layout_labels.pack_start(newcode_name_label, True, False, 3)
        newcode_layout_labels.pack_start(newcode_issuer_label, True, False, 3)
        newcode_layout_labels.pack_start(newcode_secret_label, True, False, 3)
        newcode_layout_entries.pack_start(self.newcode_name_entry, True, False, 3)
        newcode_layout_entries.pack_start(self.newcode_issuer_entry, True, False, 3)
        newcode_layout_entries.pack_start(self.newcode_secret_entry, True, False, 3)
        newcode_layout_horizontal.pack_start(newcode_layout_labels, True, False, 5)
        newcode_layout_horizontal.pack_start(newcode_layout_entries, True, False, 5)
        self.nameok = False
        self.issuerok = False
        self.secretok = False
        # connect things
        newcode_cancel_button.connect("clicked", self.newcode_cancel_button_clicked)
        self.newcode_issuer_buffer.connect("inserted-text", self.newcode_issuer_buffer_changed)
        self.newcode_name_buffer.connect("inserted-text", self.newcode_name_buffer_changed)
        self.newcode_secret_buffer.connect("inserted-text", self.newcode_secret_buffer_changed)
        self.newcode_name_buffer.connect("deleted-text", self.newcode_name_buffer_changed)
        self.newcode_issuer_buffer.connect("deleted-text", self.newcode_issuer_buffer_changed)
        self.newcode_secret_buffer.connect("deleted-text", self.newcode_secret_buffer_changed)
        self.newcode_add_button.connect("clicked", self.newcode_add_button_clicked)
        # # # # # # # # # # #
        # set up encryption #
        # # # # # # # # # # #
        encryptionsetup_layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        encryptionsetup_layout_horizontal = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        encryptionsetup_layout_spacing_h = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        encryptionsetup_layout_spacing_v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        encryptionsetup_layout_labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, homogeneous=True)
        encryptionsetup_layout_entries = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        encryptionsetup_buttonbox = Gtk.ButtonBox(orientation=Gtk.Orientation.HORIZONTAL, layout_style=Gtk.ButtonBoxStyle.EXPAND, spacing=0)
        encryptionsetup_headerlabel = Gtk.Label()
        encryptionsetup_headerlabel.set_markup('<span size="x-large">Encryption Setup</span>')
        encryptionsetup_password_label = Gtk.Label(label="Password:", xalign=0)
        encryptionsetup_confirmpass_label = Gtk.Label(label="Confirm Password:", xalign=0)
        encryptionsetup_cancel_button = Gtk.Button(label="Don't use encryption")
        self.encryptionsetup_encrypt_button = Gtk.Button(label="Encrypt", sensitive=False)
        self.encryptionsetup_encrypt_button.get_style_context().add_class("suggested-action")
        self.encryptionsetup_password_buffer = Gtk.EntryBuffer()
        self.encryptionsetup_confirmpass_buffer = Gtk.EntryBuffer()
        self.encryptionsetup_password_entry = Gtk.Entry(buffer=self.encryptionsetup_password_buffer, visibility=False)
        self.encryptionsetup_confirmpass_entry = Gtk.Entry(buffer=self.encryptionsetup_confirmpass_buffer, visibility=False)
        encryptionsetup_layout_spacing_v.set_center_widget(encryptionsetup_layout_spacing_h)
        encryptionsetup_layout_spacing_h.set_center_widget(encryptionsetup_layout)
        encryptionsetup_layout.pack_start(encryptionsetup_layout_horizontal, True, True, 6)
        encryptionsetup_layout.pack_end(encryptionsetup_buttonbox, True, False, 6)
        encryptionsetup_buttonbox.pack_start(encryptionsetup_cancel_button, True, True, 0)
        encryptionsetup_buttonbox.pack_end(self.encryptionsetup_encrypt_button, True, True, 0)
        encryptionsetup_layout_labels.pack_start(encryptionsetup_password_label, True, False, 3)
        encryptionsetup_layout_labels.pack_start(encryptionsetup_confirmpass_label, True, False, 3)
        encryptionsetup_layout_entries.pack_start(self.encryptionsetup_password_entry, True, False, 3)
        encryptionsetup_layout_entries.pack_start(self.encryptionsetup_confirmpass_entry, True, False, 3)
        encryptionsetup_layout_horizontal.pack_start(encryptionsetup_layout_labels, True, False, 5)
        encryptionsetup_layout_horizontal.pack_start(encryptionsetup_layout_entries, True, False, 5)
        # connect encryptionsetup
        self.encryptionsetup_password_buffer.connect("inserted-text", self.encryptionsetup_passwordconfirm)
        self.encryptionsetup_password_buffer.connect("deleted-text", self.encryptionsetup_passwordconfirm)
        self.encryptionsetup_confirmpass_buffer.connect("inserted-text", self.encryptionsetup_passwordconfirm)
        self.encryptionsetup_confirmpass_buffer.connect("deleted-text", self.encryptionsetup_passwordconfirm)
        self.encryptionsetup_encrypt_button.connect("clicked", self.encryptionsetup_encrypt)
        encryptionsetup_cancel_button.connect("clicked", self.encryptionsetup_dontencrypt)
        # # # # # # # # # # #
        # decryption screen #
        # # # # # # # # # # #
        decryption_layout = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        decryption_layout_spacing_h = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        decryption_layout_spacing_v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        decryption_layout_spacing_v.set_center_widget(decryption_layout_spacing_h)
        decryption_layout_spacing_h.set_center_widget(decryption_layout)
        self.decryption_password_buffer = Gtk.EntryBuffer()
        self.decryption_password_entry = Gtk.Entry(visibility=False, buffer=self.decryption_password_buffer)
        self.decrypt_button = Gtk.Button(label="Decrypt", sensitive=False)
        self.decrypt_button.get_style_context().add_class("suggested-action")
        decryption_layout.pack_start(self.decryption_password_entry, True, False, 6)
        decryption_layout.pack_end(self.decrypt_button, True, False, 6)
        self.decrypt_button.connect("clicked", self.decrypt_clicked)
        self.decryption_password_buffer.connect("inserted-text", self.decrypt_buffer_change)
        self.decryption_password_buffer.connect("deleted-text", self.decrypt_buffer_change)
        # add pages to stack
        self.stack.add_named(codeview_scolledwindow, "codeviewpage")
        self.stack.add_named(newcode_layout_spacing_v, "newcodepage")
        self.stack.add_named(encryptionsetup_layout_spacing_v, "setuppage")
        self.stack.add_named(decryption_layout_spacing_v, "decryptionpage")
        # # # # # # # #
        # start logic #
        # # # # # # # # 
        self.editmode = False
        if len(self.codelist) >= 1:
            self.headerbarbtn_editmode.set_sensitive(True)
        datafolder = Path(XDG_DATA_HOME / "GTK32FA")
        configfolder = Path(XDG_CONFIG_HOME / "GTK32FA")
        for folder in datafolder, configfolder:
            if not path.exists(folder):
                mkdir(folder)
        self.storagefile = Path(datafolder / "storage.yaml")
        self.configfile = Path(configfolder / "config.yaml")
        if path.exists(self.configfile):
            self.init_needed=False
            config = open(self.configfile, "r")
            self.configdata = yaml.safe_load(config)
            if self.configdata["dark-theme"]:
                self.settings.set_property("gtk-application-prefer-dark-theme", True)
            else:
                self.settings.set_property("gtk-application-prefer-dark-theme", False)
            if "crypto" in self.configdata and self.configdata["crypto"]:
                self.cryptoenabled = True
            else:
                self.cryptoenabled = False
                with open(self.storagefile, "rb") as storage:
                    self.filedata = StringIO(storage.read().decode("utf-8"))
            if "salt" in self.configdata and self.cryptoenabled == True:
                # = self.configdata["salt"]
                pass
            elif "salt" not in self.configdata and self.configdata["crypto"]:
                # something happened to the salt. need to make a new database if this happens, and it's not backed up.
                pass
            config.close()
        else:
            self.init_needed=True
        if self.init_needed == True:
            self.scriptsetup()
        if not self.init_needed and not self.cryptoenabled:
            if path.exists(self.storagefile):
                self.import_storage()
            else:
                open(self.storagefile, "x")
        elif not self.init_needed and self.cryptoenabled:
            self.headerbarbtn_addcode.set_sensitive(False)
            self.stack.get_child_by_name("decryptionpage").set_visible(True)
            self.stack.set_visible_child_name("decryptionpage")
        elif not self.init_needed and not self.cryptoenabled:
            self.import_storage()

    def editmode_clicked(self, widget):
        if widget.get_active() == True:
            for i in range(len(self.codelist)):
                self.codelist[i][7].set_visible_child_name("s2")
                self.editmode = True
        else:
            for i in range(len(self.codelist)):
                self.codelist[i][7].set_visible_child_name("s1")
                self.editmode = False

    def decrypt_buffer_change(self, *data):
        if self.decryption_password_buffer.get_text() == "":
            self.decrypt_button.set_sensitive(False)
        else:
            self.decrypt_button.set_sensitive(True)

    def decrypt_clicked(self, widget):
        passinput = hashlib.md5(self.decryption_password_buffer.get_text().encode("utf-8")).hexdigest()
        self.cryptokey = base64.urlsafe_b64encode(passinput.encode("utf-8"))
        self.fernetcryptokey = Fernet(self.cryptokey)
        try:
            self.filedata = StringIO()
            with open(self.storagefile, "rb") as encrypted_storage:
                encrypted_storage.seek(0)
                self.filedata.write(self.fernetcryptokey.decrypt(encrypted_storage.read()).decode("utf-8"))
                self.import_storage()
                self.stack.set_visible_child_name("codeviewpage")
                if len(self.codelist) >= 1:
                    self.headerbarbtn_editmode.set_sensitive(True)
                self.headerbarbtn_addcode.set_sensitive(True)
        except:
            self.decryption_password_entry.set_text("")
            decrypterrordlg = Gtk.MessageDialog(buttons=Gtk.ButtonsType.OK, modal=True, parent=self)
            decrypterrordlg.set_markup("<big>Failure</big>")
            decrypterrordlg.format_secondary_text("Could not open encrypted storage.\nEither the storage is damaged, or the passphrase is incorrect.\n\nIf you've forgotten the password, you can delete:\n{}/GTK32FA/config.yaml\nand the storage will be recreated on next launch.".format(str(XDG_CONFIG_HOME)))
            decrypterrordlg.run()
            decrypterrordlg.destroy()

    def commit_file_changes(self, data, encryptionenabled):
        with open(self.storagefile, "wb+") as storage:
            storage.truncate(0)
            if encryptionenabled:
                storage.write(self.fernetcryptokey.encrypt(data.encode("utf-8")))
            else:
                storage.write(data.encode("utf-8"))

    def import_storage(self):
        yaml_data = yaml.safe_load(self.filedata.getvalue())
        if yaml_data is not None:
            for i in range(len(yaml_data)):
                secret = otp.totp.TOTP(yaml_data[i][0])
                authcode = secret.now()
                self.codelist.append(tuple((authcode, secret, yaml_data[i][1], yaml_data[i][2], yaml_data[i][0])))
                self.codeviewbox.add(self.newlistrow(self.codelist[-1], -1))
                self.codeviewbox.show_all()
        if len(self.codelist) >= 1:
            self.headerbarbtn_editmode.set_sensitive(True)

    def encryptionsetup_encrypt(self, widget):
        passinput = hashlib.md5(self.encryptionsetup_password_buffer.get_text().encode("utf-8")).hexdigest()
        self.cryptokey = base64.urlsafe_b64encode(passinput.encode("ascii"))
        self.fernetcryptokey = Fernet(self.cryptokey)
        self.filedata = StringIO()
        self.filedata.write("# GTK32FA\n")
        self.commit_file_changes(self.filedata.getvalue(), True)
        with open(self.configfile, 'a') as config:
            print("crypto: true", file=config)
            print("dark-theme: false", file=config)
        config = open(self.configfile, "r")
        self.configdata = yaml.safe_load(config)
        self.cryptoenabled = True
        self.headerbarbtn_addcode.set_sensitive(True)
        self.headerbarbtn_darkmode.set_sensitive(True)
        self.headerbarbtn_editmode.set_sensitive(False)
        self.stack.set_visible_child_name("codeviewpage")

    def encryptionsetup_dontencrypt(self, widget):
        with open(self.configfile, 'a') as config:
            print("crypto: false", file=config)
            print("dark-theme: false", file=config)
        config = open(self.configfile, "r")
        self.configdata = yaml.safe_load(config)
        self.cryptoenabled = False
        self.filedata = StringIO()
        self.filedata.write("# GTK32FA\n")
        self.commit_file_changes(self.filedata.getvalue(), False)
        config.close()
        self.headerbarbtn_addcode.set_sensitive(True)
        self.headerbarbtn_darkmode.set_sensitive(True)
        self.headerbarbtn_editmode.set_sensitive(False)
        self.stack.set_visible_child_name("codeviewpage")

    def encryptionsetup_passwordconfirm(self, *data):
        if self.encryptionsetup_password_buffer.get_text() == self.encryptionsetup_confirmpass_buffer.get_text():
            self.encryptionsetup_encrypt_button.set_sensitive(True)
            self.encryptionsetup_password_entry.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, None)
        else:
            self.encryptionsetup_encrypt_button.set_sensitive(False)
            self.encryptionsetup_password_entry.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, "dialog-error")
            self.encryptionsetup_password_entry.set_icon_tooltip_text(Gtk.EntryIconPosition.SECONDARY, "Inputs do not match.")

    def scriptsetup(self):
        self.headerbarbtn_addcode.set_sensitive(False)
        self.headerbarbtn_darkmode.set_sensitive(False)
        self.stack.get_child_by_name("setuppage").set_visible(True)
        self.stack.set_visible_child_name("setuppage")

    def darkmode_clicked(self, widget):
        if self.configdata["dark-theme"]:
            darktheme = False
            self.settings.set_property("gtk-application-prefer-dark-theme", False)
        else:
            self.settings.set_property("gtk-application-prefer-dark-theme", True)
            darktheme = True
        pass
        config_rw = open(self.configfile, "w")
        self.configdata["dark-theme"] = darktheme
        yaml.safe_dump(self.configdata, config_rw)
        config_rw.close()

    def validator(self, button=None, *data):
        if False in data: 
            button.set_sensitive(False)
            return False
        else:
            button.set_sensitive(True) 
            return True

    def newcode_add_button_clicked(self, widget):
        secret_plaintext = self.newcode_secret_buffer.get_text()
        secret = otp.totp.TOTP(self.newcode_secret_buffer.get_text())
        secret_issuer = self.newcode_issuer_buffer.get_text()
        secret_name = self.newcode_name_buffer.get_text()
        authcode = secret.now()
        self.codelist.append(tuple((authcode, secret, secret_name, secret_issuer, secret_plaintext)))
        self.codeviewbox.add(self.newlistrow(self.codelist[-1], -1))
        self.codeviewbox.show_all()
        self.update_yaml()
        self.newcode_secret_entry.set_text("")
        self.newcode_name_entry.set_text("")
        self.newcode_issuer_entry.set_text("")
        self.headerbarbtn_addcode.set_sensitive(True)
        if len(self.codelist) >= 1:
            self.headerbarbtn_editmode.set_sensitive(True)
        self.stack.set_visible_child_name("codeviewpage")

    def update_yaml(self):
        storage_codelist = []
        for i in range(len(self.codelist)):
            storage_codelist.append(tuple((self.codelist[i][4], self.codelist[i][2], self.codelist[i][3])))
        yamlstr = yaml.safe_dump(storage_codelist)
        self.filedata.close()
        self.filedata = StringIO()
        self.filedata.write(yamlstr)
        if self.cryptoenabled:
            self.commit_file_changes(self.filedata.getvalue(), True)
        elif not self.cryptoenabled:
            self.commit_file_changes(self.filedata.getvalue(), False)

    def newcode_issuer_buffer_changed(self, entry_buffer=None, pos=None, chars=None, n_chars=None):
        self.issuerok = self.string_entry_buffer_handler(pos=pos, chars=chars, n_chars=n_chars, entry=self.newcode_issuer_entry, buffer=entry_buffer)
        self.validator(self.newcode_add_button, self.issuerok, self.nameok, self.secretok)

    def newcode_name_buffer_changed(self, entry_buffer=None, pos=None, chars=None, n_chars=None):
        self.nameok = self.string_entry_buffer_handler(pos=pos, chars=chars, n_chars=n_chars, entry=self.newcode_name_entry, buffer=entry_buffer)
        self.validator(self.newcode_add_button, self.issuerok, self.nameok, self.secretok)

    def newcode_secret_buffer_changed(self, entry_buffer=None, pos=None, chars=None, n_chars=None):
        self.secretok = self.b32_entry_buffer_handler(pos=pos, chars=chars, n_chars=n_chars,  entry=self.newcode_secret_entry, buffer=entry_buffer)
        self.validator(self.newcode_add_button, self.secretok, self.nameok, self.issuerok)

    def newcode_cancel_button_clicked(self, widget, *data):
        self.stack.set_visible_child_name("codeviewpage")
        self.newcode_name_entry.set_text("")
        self.newcode_issuer_entry.set_text("")
        self.newcode_secret_entry.set_text("")
        if len(self.codelist) >= 1:
            self.headerbarbtn_editmode.set_sensitive(True)
        self.headerbarbtn_addcode.set_sensitive(True)

    def string_entry_buffer_handler(self, buffer=None, pos=None, chars=None, n_chars=None, entry=None, var=None):
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

    def b32_entry_buffer_handler(self, buffer=None, pos=None, chars=None, n_chars=None, entry=None, var=None):
        if not (buffer.get_text() == ""):
            try:
                test = otp.totp.TOTP(buffer.get_text())
                test.now()
                var = True
                entry.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, None)
                return var
            except ValueError:
                entry.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, "dialog-error")
                entry.set_icon_tooltip_text(Gtk.EntryIconPosition.SECONDARY, "Not a valid secret.")
                var = False
                return var
        else:
            var = False
            return var

    def code_checker(self):
        while True:
            invalidindexes = []
            for index in range(len(self.codelist)):
                if (self.codelist[index][1].verify(self.codelist[index][0])):
                    pass
                else:
                    datalist = list(self.codelist[index])
                    datalist[0] = datalist[1].now()
                    self.codelist[index] = tuple(datalist)
                    invalidindexes.append(index)
                    self.codelist[index][5][0].set_markup(str('<span size="x-large">{}</span>').format(datalist[1].now()))
                    self.codelist[index][5][1].set_markup(str('<span size="x-large">{}</span>').format(datalist[1].now()))
                    self.codeviewbox.show_all()
                sleep(0.2)
            sleep(1)

    def newcode_clicked(self, *data):
        self.headerbarbtn_editmode.set_sensitive(False)
        self.headerbarbtn_addcode.set_sensitive(False)
        self.stack.set_visible_child_name("newcodepage")


    def delbutton_pressed(self, widget):
        for i in range(len(self.codelist)):
            if self.codelist[i][6] == widget:
                self.codelist[i][7].destroy()
                self.codelist.pop(i)
                self.update_yaml()
                break
        if len(self.codelist) >= 1:
            self.headerbarbtn_editmode.set_sensitive(True)
        else:
            self.editmode = False
            self.headerbarbtn_editmode.set_active(False)

    def newlistrow(self, codedata, givenindex, insertAt=None):
        coderow = Gtk.ListBoxRow()
        codestack = Gtk.Stack()
        codestack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        #
        # STACK1
        #
        coderow_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        coderow_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        coderow_vbox2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        coderow_hbox.pack_start(coderow_vbox, False, True, 6)
        coderow_hbox.pack_end(coderow_vbox2, False, True, 6)
        secret_name = codedata[2]
        secret_issuer = codedata[3]
        authcode = codedata[0]
        secret_name_label = Gtk.Label(xalign=0)
        secret_name_label.set_markup(str('<span style="normal" size="large">{}</span>').format(secret_name))
        secret_issuer_label = Gtk.Label(xalign=0)
        secret_issuer_label.set_markup(str('<span style="italic" foreground="darkgray">{}</span>').format(secret_issuer))
        authcode_label = Gtk.Label(xalign=1)
        authcode_label.set_markup(str('<span size="x-large">{}</span>').format(authcode))
        #
        # STACK 2
        #
        coderow_hboxs2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        coderow_vboxs2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        coderow_vbox2s2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        coderow_hboxs2.pack_start(coderow_vboxs2, False, True, 6)
        coderow_hboxs2.pack_end(coderow_vbox2s2, False, True, 6)
        secret_name_labels2 = Gtk.Label(xalign=0)
        secret_name_labels2.set_markup(str('<span style="normal" size="large">{}</span>').format(secret_name))
        secret_issuer_labels2 = Gtk.Label(xalign=0)
        secret_issuer_labels2.set_markup(str('<span style="italic" foreground="darkgray">{}</span>').format(secret_issuer))
        authcode_labels2 = Gtk.Label(xalign=1)
        authcode_labels2.set_markup(str('<span size="x-large">{}</span>').format(authcode))
        rightlayouts2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        delbutton = Gtk.Button(label="Delete")
        delbutton.get_style_context().add_class("destructive-action")
        delbutton.connect("clicked", self.delbutton_pressed)
        #
        # APPEND AUTHCODE LABELS LIST AS TUPLE AT [5][range(0,1)]
        #
        cd_l = list(codedata)
        cd_l.append(tuple((authcode_label, authcode_labels2)))
        cd_l.append(delbutton)
        cd_l.append(codestack)
        self.codelist[givenindex] = tuple(cd_l)
        #
        # PACKING STACK1
        #
        coderow_vbox.pack_start(secret_name_label, True, True, 6)
        coderow_vbox.pack_start(secret_issuer_label, True, True, 6)
        coderow_vbox2.set_center_widget(self.codelist[-1][5][0])
        #
        # PACKING STACK2
        #
        coderow_vboxs2.pack_start(secret_name_labels2, True, True, 6)
        coderow_vboxs2.pack_start(secret_issuer_labels2, True, True, 6)
        coderow_vbox2s2.set_center_widget(rightlayouts2)
        rightlayouts2.pack_start(self.codelist[-1][5][1], True, True, 0)
        rightlayouts2.pack_start(self.codelist[-1][6], False, False, 6)
        #
        # ADD STACKS TO STACK
        #
        codestack.add_named(coderow_hbox, "s1")
        codestack.add_named(coderow_hboxs2, "s2")
        if self.editmode:
            codestack.get_child_by_name("s2").show_all()
            codestack.set_visible_child_name("s2")
        coderow.add(codestack)
        if insertAt is None:
            self.rowlist.append(coderow)
        else:
            self.rowlist.insert(insertAt, coderow)
        return self.rowlist[-1]

# show the starting window
#GObject.threads_init()
startWindow = MainWindow()
startWindow.show_all()
Gtk.main()