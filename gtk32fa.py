#!/usr/bin/env python3
# imports
import gi
import pyotp as otp
import threading
from time import sleep
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GObject, Gio

class MainWindow(Gtk.Window):
    def __init__(self):
        self.codelist = []
        self.authcodelabellist = []
        self.rowlist = []
        Gtk.Window.__init__(self)
        # set up window parameters
        self.set_title("GTK32FA")
        self.set_default_size(640, 640)
        # make a headerbar for the window
        headerbar = Gtk.HeaderBar(title="GTK32FA", show_close_button=True)
        self.set_titlebar(headerbar)
        # headerbar buttons
        headerbarbtn_addcode = Gtk.Button.new_from_icon_name("list-add", Gtk.IconSize.BUTTON)
        headerbar.pack_start(headerbarbtn_addcode)
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
        headerbarbtn_addcode.connect("clicked", self.newcode_clicked, self.codeviewbox)
        code_validation_thread = threading.Thread(target=self.code_checker, daemon=True)
        code_validation_thread.start()
        #
        # new code page
        #
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
        # add pages to stack
        self.stack.add_named(codeview_scolledwindow, "codeviewpage")
        self.stack.add_named(newcode_layout_spacing_v, "newcodepage")

    def validator(self, button=None, *data):
        if False in data: 
            button.set_sensitive(False)
            return False
        else:
            button.set_sensitive(True) 
            return True

    def newcode_add_button_clicked(self, widget):
        secret = otp.totp.TOTP(self.newcode_secret_buffer.get_text())
        secret_issuer = self.newcode_issuer_buffer.get_text()
        secret_name = self.newcode_name_buffer.get_text()
        authcode = secret.now()
        idnumber = len(self.codelist)+1
        self.codelist.append(tuple((authcode, secret, secret_name, secret_issuer, idnumber)))
        self.codeviewbox.add(self.newlistrow(self.codelist[-1]))
        self.codeviewbox.show_all()
        self.newcode_secret_entry.set_text("")
        self.newcode_name_entry.set_text("")
        self.newcode_issuer_entry.set_text("")
        self.stack.set_visible_child_name("codeviewpage")

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
                entry.set_icon_tooltip_text(Gtk.EntryIconPosition.SECONDARY, "Not valid Base32.")
                var = False
                return var
        else:
            var = False
            return var

    def code_checker(self):
        while True:
            invalidindexes = []
            for index in range(len(self.codelist)):
                print("Confirming code at indexno" + str(index))
                if (self.codelist[index][1].verify(self.codelist[index][0])):
                    print("OTP Code " + str(self.codelist[index][0]) + " at list index number" + str(index) + " is valid.")
                else:
                    print("OTP Code " + str(self.codelist[index][0]) + " at list index number" + str(index) + " is invalid.")
                    print("Regenerating code...")
                    datalist = list(self.codelist[index])
                    datalist[0] = datalist[1].now()
                    print("New code for "  + str(self.codelist[index][2]) + " is " + str(self.codelist[index][0]))
                    invalidindexes.append(index)
                    self.authcodelabellist[index].set_markup(str('<span size="x-large">{}</span>').format(datalist[1].now()))
                    self.codeviewbox.show_all()
                sleep(0.2)
            print("List checked. Waiting 15 seconds...")
            sleep(1)

    def newcode_clicked(self, *data):
        self.stack.set_visible_child_name("newcodepage")

    def newlistrow(self, codedata, insertAt=None):
        coderow = Gtk.ListBoxRow()
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
        self.authcodelabellist.append(authcode_label)
        coderow_vbox.pack_start(secret_name_label, True, True, 6)
        coderow_vbox.pack_start(secret_issuer_label, True, True, 6)
        coderow_vbox2.set_center_widget(self.authcodelabellist[-1])
        coderow.add(coderow_hbox)
        if insertAt is None:
            self.rowlist.append(coderow)
        else:
            self.rowlist.insert(insertAt, coderow)
        return self.rowlist[-1]

class DecryptionWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self)
        # stub


# show the starting window
#GObject.threads_init()
startWindow = MainWindow()
startWindow.show_all()
Gtk.main()
