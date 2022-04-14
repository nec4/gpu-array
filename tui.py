import curses
from query import *
from time import sleep
from threading import Thread, Event


def curses_init():
    screen = curses.initscr()
    curses.noecho()
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, 2, -1)  # low
    curses.init_pair(2, 3, -1)  # medium
    curses.init_pair(3, 1, -1)  # high
    screen.keypad(1)
    screen.idcok(False)
    screen.nodelay(1)
    return screen


class PollThread(Thread):
    """Thread for polling GPU information

    Parameters
    ----------
    tracker:
        GPU

    """
    def __init__(self, tracker):
        Thread.__init__(self)
        self.stop_event = Event()
        self.tracker = tracker

    def run(self):
        while(not self.stop_event.isSet()):
            self.tracker.poll()
            sleep(1)

    def join(self, timeout=None):
        self.stop_event.set()
        Thread.join(self, timeout=timeout)

class FrontEnd(object):
    """TUI for GPU information"""

    overwatch_labels = {
        "memory": "Mem ",
        "temperature": "Tmp ",
        "power": "Pwr ",
        "fan": "Fan ",
    }
    process_labels = {"pid": "PID  ", "memory": "Mem  ", "name": "Name "}

    card_buffer_y = 11
    card_buffer_x = 11

    def __init__(self, tracker, rows, cols):
        self.tracker = tracker
        self.poll_thread = None
        self.indent = 4
        self.current_view = "overwatch"
        self.resize(rows, cols)

    def resize(self, rows, cols):
        self.rows, self.cols = rows, cols
        self._initialize_gpu_windows()

    def run(self):
        self.poll_thread = PollThread(self.tracker)
        self.poll_thread.start()

    def stop(self):
        self.poll_thread.join()

    def clear_array(self):
        for win_row in self.window_array:
            for window in win_row:
                window.clear()
                window.border(*[0 for _ in range(8)])

    def _swap_view(self):
        if self.current_view == "overwatch":
            self.current_view = "process"
            self.clear_array()
            return None
        if self.current_view == "process":
            self.current_view = "overwatch"
            self.clear_array()
            return None

    def draw(self):
        if self.current_view == "overwatch":
            self._draw_overwatch()
        if self.current_view == "process":
            self._draw_process()

    def _initialize_gpu_windows(self):
        # screen will broken into n squares
        # where n is the nearest power of two
        powers = [i**2 for i in range(1, 4)]
        diffs = [i- self.tracker.num_gpus for i in powers]
        _, idx = min((val, idx) for (idx, val) in enumerate(diffs) if val >= 0)
        num_windows = powers[idx]
        win_rows = idx + 1
        self.win_rows = win_rows
        win_size_y = (self.rows // win_rows) - 1
        win_size_x = (self.cols // win_rows) - 1

        if win_size_y <= FrontEnd.card_buffer_y:
            curses.endwin()
            self.stop()
            raise RuntimeError("Terminal too small in Y!")
        if win_size_x <= FrontEnd.card_buffer_x:
            curses.endwin()
            self.stop()
            raise RuntimeError("Terminal too small in X!")

        self.window_array = [
            [
                curses.newwin(win_size_y, win_size_x, i * win_size_y, j * win_size_x)
                for j in range(win_rows)
            ]
            for i in range(win_rows)
        ]

        for i in range(len(self.window_array)):
            for j in range(len(self.window_array)):
                self.window_array[i][j].border(*[0 for _ in range(8)])
                self.window_array[i][j].scrollok(1)


    @staticmethod
    def _determine_color(val):
        if val < 33:
            color = curses.color_pair(1)
        elif val > 33 and val < 66:
            color = curses.color_pair(2)
        else:
            color = curses.color_pair(3)
        return color

    def _draw_process(self):
        all_gpu_props = self.tracker.props_buffer
        if all_gpu_props != None:
            gpu_ids = sorted(all_gpu_props.keys())
            for gpu_id in gpu_ids:
                row = gpu_id // self.win_rows
                col = gpu_id % self.win_rows
                window = self.window_array[row][col]
                processes = all_gpu_props[gpu_id]["processes"].keys()
                try:
                    window.addstr(
                        1,
                        1,
                        " {}: {} ".format(gpu_id, all_gpu_props[gpu_id]["name"]),
                    )
                    for i, process in enumerate(processes):
                        proc = all_gpu_props[gpu_id]["processes"][process]
                        proc_string = "{}: {} {} {} {}".format(
                            proc["user"], process, proc["name"], proc["lifetime"], proc["mem"]
                        )
                        window.addstr(2 + i, self.indent, proc_string)
                except:
                    window.addstr(1,1,"Expand terminal - currently too small ...")

    def _draw_overwatch(self):
        all_gpu_props = self.tracker.props_buffer
        if all_gpu_props != None:
            gpu_ids = sorted(all_gpu_props.keys())
            for gpu_id in gpu_ids:
                row = gpu_id // self.win_rows
                col = gpu_id % self.win_rows

                mem_string = "{}{}/{}".format(
                    FrontEnd.overwatch_labels["memory"],
                    all_gpu_props[gpu_id]["used_mem"],
                    all_gpu_props[gpu_id]["total_mem"],
                )
                fan_string = "{}{} %".format(
                    FrontEnd.overwatch_labels["fan"], int(all_gpu_props[gpu_id]["fan"])
                )
                temp_string = "{}{}/{}".format(
                    FrontEnd.overwatch_labels["temperature"],
                    int(all_gpu_props[gpu_id]["temp"]),
                    int(all_gpu_props[gpu_id]["max_temp"]),
                )
                power_string = "{}{}/{}".format(
                    FrontEnd.overwatch_labels["power"],
                    int(all_gpu_props[gpu_id]["used_power"]),
                    int(all_gpu_props[gpu_id]["power_limit"]),
                )

                mem_frac = int(
                    100
                    * (
                        all_gpu_props[gpu_id]["used_mem"]
                        / all_gpu_props[gpu_id]["total_mem"]
                    )
                )
                power_frac = int(
                    100
                    * (
                        all_gpu_props[gpu_id]["used_power"]
                        / all_gpu_props[gpu_id]["power_limit"]
                    )
                )
                temp_frac = int(
                    100
                    * (all_gpu_props[gpu_id]["temp"] / all_gpu_props[gpu_id]["max_temp"])
                )
                fan_frac = all_gpu_props[gpu_id]["fan"]

                fan_color = FrontEnd._determine_color(fan_frac)
                mem_color = FrontEnd._determine_color(mem_frac)
                power_color = FrontEnd._determine_color(power_frac)
                temp_color = FrontEnd._determine_color(temp_frac)

                window = self.window_array[row][col]
                window.addstr(
                    1,
                    1,
                    " {}: {} ".format(gpu_id, all_gpu_props[gpu_id]["name"]),
                )
                window.addstr(
                    2,
                    self.indent,
                    mem_string,
                    mem_color,
                )
                self.draw_bar(window, 3, self.indent, mem_frac, mem_color)

                window.addstr(
                    4,
                    self.indent,
                    fan_string,
                    fan_color,
                )
                self.draw_bar(window, 5, self.indent, fan_frac, fan_color)

                window.addstr(6, self.indent, temp_string, temp_color)
                self.draw_bar(window, 7, self.indent, temp_frac, temp_color)

                window.addstr(8, self.indent, power_string, power_color)
                self.draw_bar(window, 9, self.indent, power_frac, power_color)

    def draw_bar(self, window, y, x, percent, color):
        _, size_x = window.getmaxyx()
        length = size_x - x - 4
        filled = int(length * (percent / 100.0))
        unfilled = length - filled
        window.addstr(y, x, "[")
        window.addstr(
            y, x + 1, "".join([" " for i in range(filled)]), curses.A_REVERSE | color
        )
        window.addstr(y, x + filled, "".join([" " for i in range(unfilled)]))
        window.addstr(y, x + filled + unfilled, "]")

    def refresh_array(self):
        for i in range(len(self.window_array)):
            for j in range(len(self.window_array)):
                window = self.window_array[i][j]
                y_i, x_i = window.getbegyx()
                y, x = window.getmaxyx()
                self.window_array[i][j].refresh()
                # self.pad_array[i][j].refresh(0,0, y_i+2,x_i+2, y_i+y-2, x_i+x-2)

    def refresh(self, screen):
        self.draw()
        screen.refresh()
        self.refresh_array()
