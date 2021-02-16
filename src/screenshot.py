# screenshot.py
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

# adapted from https://gitlab.gnome.org/World/Authenticator

from os import path
from tempfile import NamedTemporaryFile
from gi.repository import Gio, GLib


class GNOMEScreenshot:
    """
        GNOME Screenshot interface implementation.
        Currently implements the only needed method by Authenticator.
    """
    interface = "org.gnome.Shell.Screenshot"
    path = "/org/gnome/Shell/Screenshot"

    def __init__(self):
        pass

    @staticmethod
    def area(filename: str = None) -> str:
        """
            Take a screen shot of an area and save it to a specific filename
            Using GNOME Shell Screenshot Interface.
            :param filename: output filename
            :type filename: str
        """
        if not filename:
            filename = path.join(GLib.get_user_cache_dir(),
                                 path.basename(NamedTemporaryFile().name))
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        screen_proxy = Gio.DBusProxy.new_sync(bus,
                                              Gio.DBusProxyFlags.NONE,
                                              None,
                                              GNOMEScreenshot.interface,
                                              GNOMEScreenshot.path,
                                              GNOMEScreenshot.interface,
                                              None)
        x, y, width, height = screen_proxy.call_sync('SelectArea', None, Gio.DBusCallFlags.NONE,
                                                     -1, None).unpack()

        args = GLib.Variant('(iiiibs)', (x, y, width, height, False, filename
                                         )
                            )
        screenshot = screen_proxy.call_sync('ScreenshotArea', args,
                                            Gio.DBusCallFlags.NONE, -1, None)
        success, filename = screenshot.unpack()
        return filename if success else None
