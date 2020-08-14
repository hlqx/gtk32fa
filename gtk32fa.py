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
		self.rowmodel = Gio.ListStore.new(Gtk.ListBoxRow)
		Gtk.Window.__init__(self)
		# set up window parameters
		self.set_interactive_debugging(True)
		self.set_title("2Factor")
		self.set_default_size(640, 640)
		# make a headerbar for the window
		headerbar = Gtk.HeaderBar(title="2Factor", subtitle="0 codes in database", show_close_button=True)
		self.set_titlebar(headerbar)
		# headerbar buttons
		headerbarbtn_addcode = Gtk.Button.new_from_icon_name("list-add", Gtk.IconSize.BUTTON)
		headerbar.pack_start(headerbarbtn_addcode)
		# connect window close to window fucking dying
		self.connect("destroy", Gtk.main_quit)
		# stack control, make it main widget for window
		stack = Gtk.Stack()
		stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
		self.add(stack)
		# make a scrolledwindow component
		codeview_scolledwindow = Gtk.ScrolledWindow()
		# list view test
		self.codeviewbox = Gtk.ListBox()
		self.codeviewbox.set_selection_mode(Gtk.SelectionMode.NONE)
		# add the codeview to the scrolledwindow
		codeview_scolledwindow.add(self.codeviewbox)
		# add the code view to the stack
		stack.add_named(codeview_scolledwindow, "codeview")
		# connect new button to it's function
		headerbarbtn_addcode.connect("clicked", self.newcode_clicked, self.codeviewbox)
		code_validation_thread = threading.Thread(target=self.code_checker, daemon=True)
		code_validation_thread.start()

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
					self.codelist[index] = datalist
					print("New code for "  + str(self.codelist[index][2]) + " is " + str(self.codelist[index][0]))
					invalidindexes.append(index)
					self.authcodelabellist[index].set_markup(str('<span size="x-large">{}</span>').format(datalist[1].now()))
					self.codeviewbox.show_all()
				sleep(0.2)
			print("List checked. Waiting 15 seconds...")
			sleep(1)

	def newcode_clicked(self, *data):
		self.newcode(self.codelist)
		data[1].add(self.newlistrow(self.codelist[-1]))
		data[1].show_all()

	def newcode(self, *data):
		secret = otp.totp.TOTP(otp.random_base32())
		authcode = secret.now()
		secret_name = "John Smith"
		secret_issuer = "Issuer"
		idnumber = len(self.codelist)+1
		self.codelist.append(tuple((authcode, secret, secret_name, secret_issuer, idnumber)))
		return

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
