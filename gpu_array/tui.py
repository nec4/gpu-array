import urwid
from .query import GPUQuery, Tracker
from time import sleep
from threading import Thread, Event
from typing import Union, List


class PollThread(Thread):
    """Thread for polling GPU information

    Parameters
    ----------
    tracker:
        Tracker instance for requesting, parsing and storing
        GPU information.
    """

    def __init__(self, tracker: Tracker):
        Thread.__init__(self)
        self.stop_event = Event()
        self.tracker = tracker

    def run(self):
        """Main thread polling loop. Sleeps 1s after each poll."""
        while not self.stop_event.isSet():
            self.tracker.poll()
            sleep(self.tracker.polling_rate)

    def join(self, timeout: Union[int, None] = None):
        """Safely request thread to end

        Parameters
        ----------
        timeout:
            Number of seconds to wait before thread join attempt ends.
        """
        self.stop_event.set()
        Thread.join(self, timeout=timeout)


class FrontEnd(object):
    """TUI for GPU information. Uses an additional thread to run
    polling requests from the GPU tracker. During the main loop,
    "q" quits and "p" toggles GPU statistics and process information.

    Parameters
    ----------
    tracker:
        Tracker instance for requesting, parsing and storing
        GPU information.
    """

    box_padding = 1
    card_width = 35
    overwatch_labels = {
        "memory": "Mem ",
        "temperature": "Tmp ",
        "power": "Pwr ",
        "fan": "Fan ",
    }
    process_labels = {"pid": "PID  ", "memory": "Mem  ", "name": "Name "}

    palette = [
        ("low", "dark green", ""),
        ("medium", "brown", ""),
        ("high", "dark red", ""),
        ("rev_inc", "black", "light gray"),
        ("rev", "", "black"),
        ("cuda", "light gray", "dark blue"),
        ("driver", "light gray", "dark magenta"),
    ]

    def __init__(self, tracker):
        self.current_view = "overwatch"
        self.top = None
        self.tracker = tracker
        self._initialize_grid()
        self.loop = urwid.MainLoop(
            self.top, palette=FrontEnd.palette, unhandled_input=self.keypress
        )
        self.loop.set_alarm_in(sec=1, callback=self._draw)

    def _switch_view(self):
        """Swaps current card view after detecting 'p' keypress"""
        if self.current_view == "overwatch":
            self.current_view = "process"
            self._initialize_grid()
            return None
        if self.current_view == "process":
            self.current_view = "overwatch"
            self._initialize_grid()
            return None

    def start(self):
        """Creates and starts the polling thread as well as the TUI main loop"""
        self.poll_thread = PollThread(self.tracker)
        self.poll_thread.start()
        self.loop.run()

    def stop(self):
        """Joins the polling thread and exits the TUI main loop"""
        self.poll_thread.join()
        raise urwid.ExitMainLoop()

    def keypress(self, key: str):
        """Input handling

        Parameters
        ----------
        key:
            Pressed key
        """
        if key in (
            "q",
            "Q",
        ):
            self.stop()
        if key in ("p",):
            self._switch_view()

    @staticmethod
    def _initialize_gauge_card() -> urwid.LineBox:
        """Method for initializing the visual GPU cards. Each card
        is represented with a LineBox-wrapped Pile widget. Within
        the Pile widget, several sub widgets are enumerated:

        LineBox:
          Pile:
            1: Text -> (GPU name)
            2: Padding(Text) -> Memory string
            3: Padding(ProgressBar) -> Memory fraction
            4: Padding(Text) -> Fan string
            5: Padding(ProgressBar) -> Fan fraction
            6: Padding(Text) -> Temperature string
            7: Padding(ProgressBar) -> Temperature fraction
            8: Padding(Text) -> Power string
            9: Padding(ProgressBar) -> Power fraction
        """
        pile = []
        pile.append(urwid.Text(""))
        for _ in range(4):
            pile.append(urwid.Padding(urwid.Text(""), left=2))
            pile.append(
                urwid.Padding(
                    urwid.ProgressBar("rev", "rev_inc", current=0),
                    width=("relative", 90),
                    align="center",
                )
            )
        box = urwid.LineBox(urwid.Pile(pile))
        return box

    @staticmethod
    def _initialize_proc_card() -> urwid.LineBox:
        """Method for initializing the process GPU cards. Each card
        is represented with a LineBox-wrapped Pile widget. Within
        the Pile widget, several sub widgets are enumerated:

        LineBox:
          Pile:
            1: Text -> (GPU name)
            2: Padding(Text) -> Process string
        """

        pile = []
        pile.append(urwid.Text(""))
        pile.append(urwid.Padding(urwid.Text(""), left=2))
        box = urwid.LineBox(urwid.Pile(pile))
        return box

    def _update_proc_pile(self, name_str: str, proc_strs: List[str]) -> urwid.LineBox:
        """Method for updating/filling out a process card

        Parameters
        ----------
        name_str:
            GPU name
        proc_strs:
            List of process information strings

        Returns
        -------
        box:
            GPU process card
        """
        pile = []
        pile.append(urwid.Text(name_str))
        for p in enumerate(proc_strs):
            pile.append(urwid.Padding(urwid.Text(p), left=2))
        box = urwid.LineBox(urwid.Pile(pile))
        return box

    def _initialize_grid(self):
        """Method for initializing the GPU card grid using urwid.GridFlow"""
        if self.current_view == "overwatch":
            card_list = [
                FrontEnd._initialize_gauge_card() for _ in range(self.tracker.num_gpus)
            ]
        if self.current_view == "process":
            card_list = [
                FrontEnd._initialize_proc_card() for _ in range(self.tracker.num_gpus)
            ]
        self.grid = urwid.GridFlow(
            card_list,
            FrontEnd.card_width,
            FrontEnd.box_padding,
            FrontEnd.box_padding,
            "center",
        )
        header = urwid.Text(
            [
                ("cuda", " CUDA {} ".format(self.tracker.cuda_version)),
                ("driver", " Driver {} ".format(self.tracker.driver_version)),
            ]
        )
        if self.top == None:
            self.top = urwid.Frame(
                body=urwid.Filler(self.grid), header=header, footer=None
            )
        else:
            self.top.contents["body"][0].original_widget = self.grid

    @staticmethod
    def _determine_color(val: int) -> str:
        """Helper method to determine color depending
        on severity of the input value.

        Parameters
        ----------
        val:
            input value that should range from 0 to 100

        Returns
        -------
        color:
            urwid palette key
        """
        if val < 33:
            color = "low"
        elif val > 33 and val < 66:
            color = "medium"
        else:
            color = "high"
        return color

    def _draw(self, *args):
        """Depending on the current view, runs drawing routines"""
        if self.current_view == "overwatch":
            self._draw_overwatch()
        if self.current_view == "process":
            self._draw_process()
        self.loop.set_alarm_in(1, self._draw)

    def _draw_process(self):
        """Method for drawing process information to each GPU window"""
        all_gpu_props = self.tracker.props_buffer
        if all_gpu_props != None:
            gpu_ids = sorted(all_gpu_props.keys())
            card_list = []
            for gpu_id in gpu_ids:
                name_string = all_gpu_props[gpu_id]["name"]
                processes = all_gpu_props[gpu_id]["processes"].keys()
                proc_strs = []
                for i, process in enumerate(processes):
                    proc = all_gpu_props[gpu_id]["processes"][process]
                    proc_string = "{}: {} {} {} {}".format(
                        proc["user"],
                        process,
                        proc["name"],
                        proc["lifetime"],
                        proc["mem"],
                    )
                    proc_strs.append(proc_string)
                card_list.append(self._update_proc_pile(name_string, proc_strs))
            self.grid = urwid.GridFlow(
                card_list,
                FrontEnd.card_width,
                FrontEnd.box_padding,
                FrontEnd.box_padding,
                "center",
            )
            self.top.contents["body"][0].original_widget = self.grid

    def _draw_overwatch(self, *args):
        """Method for drawing stats information to each GPU window"""
        all_gpu_props = self.tracker.props_buffer
        if all_gpu_props != None:
            gpu_ids = sorted(all_gpu_props.keys())
            for gpu_id in gpu_ids:
                name_string = all_gpu_props[gpu_id]["name"]
                mem_string = "{}{}/{} MiB".format(
                    FrontEnd.overwatch_labels["memory"],
                    all_gpu_props[gpu_id]["used_mem"],
                    all_gpu_props[gpu_id]["total_mem"],
                )
                fan_string = "{}{} %".format(
                    FrontEnd.overwatch_labels["fan"], int(all_gpu_props[gpu_id]["fan"])
                )
                temp_string = "{}{}/{} C".format(
                    FrontEnd.overwatch_labels["temperature"],
                    int(all_gpu_props[gpu_id]["temp"]),
                    int(all_gpu_props[gpu_id]["max_temp"]),
                )
                power_string = "{}{}/{} W".format(
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
                    * (
                        all_gpu_props[gpu_id]["temp"]
                        / all_gpu_props[gpu_id]["max_temp"]
                    )
                )
                fan_frac = all_gpu_props[gpu_id]["fan"]

                card_contents = (
                    self.top.contents["body"][0]
                    .original_widget.contents[gpu_id][0]
                    .original_widget.contents
                )
                card_contents[0][0].set_text(name_string)
                card_contents[1][0].original_widget.set_text(
                    (self._determine_color(mem_frac), mem_string)
                )
                card_contents[2][0].original_widget.set_completion(mem_frac)
                card_contents[3][0].original_widget.set_text(
                    (self._determine_color(fan_frac), fan_string)
                )
                card_contents[4][0].original_widget.set_completion(fan_frac)
                card_contents[5][0].original_widget.set_text(
                    (self._determine_color(temp_frac), temp_string)
                )
                card_contents[6][0].original_widget.set_completion(temp_frac)
                card_contents[7][0].original_widget.set_text(
                    (self._determine_color(power_frac), power_string)
                )
                card_contents[8][0].original_widget.set_completion(power_frac)
