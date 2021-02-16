# main.py
#
# Copyright 2021 Niall Asher
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

from datetime import date, datetime

class InfoLogger:

    """
        Print an error to the screen
    """
    def stdout_log(errortext, logtype="none"):
        now = datetime.now()
        if logtype == "failure":
            icon = "❌ "
        elif logtype == "info":
            icon = "ℹ️ "
        elif logtype == "success":
            icon = "✅ "
        elif logtype == "wait":
            icon = "⏰ "
        elif logtype == "none":
            icon = ""
        else:
            icon = ""
        timestamp = now.strftime("%H:%M:%S")
        print(f"[{timestamp}] {icon} {errortext}")
