# Copyright 2023 Matthew Reid.
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import re
import subprocess
import tkinter as tk
import tkinter.messagebox as messagebox
import tkinter.scrolledtext as scrolledtext
import tkinter.ttk as ttk
from datetime import datetime, timedelta
from typing import Optional, Sequence


def start_frame(project: str, tags: Sequence[str], no_gap: bool):
    tag_strs = [f"+{tag}" for tag in tags]
    no_gap_str = "--no-gap" if no_gap else ""
    subprocess.run(f"watson start {project} {' '.join(tag_strs)} {no_gap_str}")


def stop_frame():
    subprocess.run("watson stop")


def execute_command(command: str) -> bytes:
    return subprocess.run(command, stdout=subprocess.PIPE).stdout


def show_message_dialog(message: str):
    dialog = tk.Toplevel(window)
    text = scrolledtext.ScrolledText(dialog)
    text.insert(tk.END, message)
    text.configure(state="disabled")
    text.pack()
    dialog.grab_set()


def show_log():
    show_message_dialog(execute_command("watson log"))


def show_csv():
    show_message_dialog(execute_command("watson report --csv"))


def get_current_start_time() -> Optional[datetime]:
    result = str(execute_command("watson status"))
    if "No project started" in result:
        return None
    else:
        time_result = re.findall(r'\(.*?\)', result)
        if len(time_result) != 1:
            raise Exception("Unexpected time format returned by 'watson status' command")
        return datetime.strptime(time_result[0], "(%Y.%m.%d %H:%M:%S%z)").replace(tzinfo=None)


def get_projects() -> Sequence[str]:
    return execute_command("watson projects").splitlines()


def get_tags() -> Sequence[str]:
    return execute_command("watson tags").splitlines()


def set_button_enabled(button: tk.Button, enabled: bool):
    if enabled:
        button.config(state="normal")
    else:
        button.config(state="disabled")


class TimerLabelUpdater():
    def __init__(self, label: tk.Label, start_time: Optional[datetime] = None):
        self.label = label
        self.start_time = start_time
        self._update_label()

    def set_start_time(self, start_time: Optional[datetime]):
        self.start_time = start_time

    def _update_label(self):
        dt = datetime.now().replace(microsecond=0) - self.start_time if self.start_time else timedelta()
        self.label.configure(text=str(dt))
        self.label.after(1000, self._update_label)


class ComboboxList(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.comboboxes = []
        self.combobox_values = []
        self.options = []

        self._add_item()

    def set_options(self, options: Sequence[str]):
        self.options = options
        for combobox in self.comboboxes:
            combobox["values"] = options

    def get_values(self) -> Sequence[str]:
        return [combobox.get() for combobox in self.comboboxes if combobox.get() != None]

    def _add_item(self):
        combobox = ttk.Combobox(self, values=self.options)
        combobox.pack()
        self.comboboxes.append(combobox)

        def on_combobox_selected(*args):
            nonlocal combobox
            if combobox.get()=="" and len(self.comboboxes) > 1:
                index = self.comboboxes.index(combobox)
                del self.comboboxes[index]
                del self.combobox_values[index]
                combobox.destroy()
            else:
                if self.comboboxes[len(self.comboboxes)-1] == combobox:
                    self._add_item()

        value = tk.StringVar()
        value.trace('w', on_combobox_selected)
        self.combobox_values.append(value)
        combobox.configure(textvariable=value)


window = tk.Tk()
window.title("Watson GUI")

params_frame = tk.Frame(window)
params_frame.grid(row=0, column=0, padx=10)

tk.Label(params_frame, text="Project").grid(row=0, column=0)
projects = get_projects()
project_combo = ttk.Combobox(params_frame, values=projects)
project_combo.current(None if not projects else 0)
project_combo.grid(row=0, column=1, pady=10)

tk.Label(params_frame, text="Tags").grid(row=1, column=0)
tags_list = ComboboxList(params_frame)
tags_list.set_options(get_tags())
tags_list.grid(row=1, column=1, pady=10)

current_start_time = get_current_start_time()

ttk.Label(params_frame, text="Start at").grid(row=2, column=0)

start_at_combo = ttk.Combobox(params_frame, state="readonly", values=("Now", "Last stop time"))
start_at_combo.current(0)
start_at_combo.grid(row=2, column=1, pady=10)

time_label = ttk.Label(window, font="Verdana 30 bold")
time_label.grid(row=1, column=0, pady=10)
time_label_updater = TimerLabelUpdater(time_label, current_start_time)

buttons_frame = tk.Frame(window)
buttons_frame.grid(row=2, column=0)

button_width = 14

start_button = ttk.Button(buttons_frame, text="Start", width=button_width)
start_button.grid(row=0, column=0)
set_button_enabled(start_button, current_start_time==None)

stop_button = ttk.Button(buttons_frame, text="Stop", width=button_width)
stop_button.grid(row=0, column=1, pady=10)
set_button_enabled(stop_button, current_start_time!=None)

def on_start_commanded():
    if not project_combo.get():
        messagebox.showerror(title=None, message="Project name cannot be empty")
        return

    start_frame(project_combo.get(), tags_list.get_values(), start_at_combo.current())
    time_label_updater.set_start_time(get_current_start_time())
    set_button_enabled(start_button, False)
    set_button_enabled(stop_button, True)
start_button.configure(command=on_start_commanded)

def on_stop_commanded():
    stop_frame()
    project_combo["values"] = get_projects()
    tags_list.set_options(get_tags())
    time_label_updater.set_start_time(None)
    set_button_enabled(start_button, True)
    set_button_enabled(stop_button, False)
stop_button.configure(command=on_stop_commanded)

ttk.Button(buttons_frame, text="Show Log", command=show_log, width=button_width).grid(row=1, column=0, pady=10)
ttk.Button(buttons_frame, text="Show CSV", command=show_csv, width=button_width).grid(row=1, column=1)

window.mainloop()