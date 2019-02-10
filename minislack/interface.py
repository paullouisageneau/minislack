
import curses
import threading
import _thread
import re

DEFAULT_CHANNEL = "random"

GETCH_READ_TIMEOUT = 200

NORMAL_COLOR_PAIR = 1
HIGHLIGHT_COLOR_PAIR = 2
INPUT_COLOR_PAIR = 3


class Interface:
    def __init__(self, send_func):
        self.send_func = send_func
        self.messages = []
        self.input = ""
        self.input_position = 0
        self.input_channel = None
        self.channel = DEFAULT_CHANNEL
        self.condition = threading.Condition()
        self.curses_thread = None
        self.stopped = False

    def recv(self, channel, message):
        with self.condition:
            self.messages.append((channel, message))
            self.condition.notify()

    def send(self, channel, message):
        self.send_func(channel, message)

    def clear(self):
        with self.condition:
            self.messages = []
            self.input = ""
            self.input_position = 0
            self.input_channel = None
            self.condition.notify()

    def start(self):

        def curses_main(stdscr):
            if curses.has_colors():
                curses.start_color()
                curses.init_pair(NORMAL_COLOR_PAIR, curses.COLOR_WHITE, curses.COLOR_BLACK)
                curses.init_pair(HIGHLIGHT_COLOR_PAIR, curses.COLOR_GREEN, curses.COLOR_BLACK)
                curses.init_pair(INPUT_COLOR_PAIR, curses.COLOR_BLUE, curses.COLOR_BLACK)
                stdscr.attrset(NORMAL_COLOR_PAIR)
            stdscr.clear()
            stdscr.refresh()
            sy, sx = stdscr.getmaxyx()
            win = curses.newwin(sy-1, sx, 0, 0)
            win.scrollok(True)
            win.idlok(True)
            input_win = curses.newwin(1, sx, sy-1, 0)
            index = 0

            def refresh():
                nonlocal index
                if index > len(self.messages):
                    win.clear()
                    index = 0
                while index < len(self.messages):
                    channel, message = self.messages[index]
                    attr = curses.color_pair(HIGHLIGHT_COLOR_PAIR) | curses.A_BOLD
                    if self.channel != channel:
                        self.channel = channel
                        win.addstr("{}> ".format(channel), attr)
                    else:
                        win.addstr("> ", attr)
                    blink = re.search('(^|\\W)!\\w+', message) is not None
                    attr = curses.color_pair(NORMAL_COLOR_PAIR) | (curses.A_BLINK if blink else 0)
                    win.addstr("{}\n".format(message), attr)
                    index += 1
                win.refresh()
                if len(self.input) > sx-3:
                    self.input = self.input[:sx-3]
                    curses.beep()
                attr = curses.color_pair(INPUT_COLOR_PAIR) | curses.A_BOLD
                input_win.attrset(attr)
                input_win.erase()
                if self.input_channel:
                    channel = self.input_channel
                    position = self.input_position
                    input_win.addstr(0, 0, "{}> {}".format(channel, self.input))
                    input_win.addstr(0, 0, "{}> {}".format(channel, self.input[:position]))
                input_win.refresh()

            input_thread = threading.Thread(target=input_main, args=(stdscr,))
            input_thread.start()

            with self.condition:
                while not self.stopped:
                    refresh()
                    self.condition.wait()

            input_thread.join()

        def input_main(stdscr):
            input_bytes = b""

            def process(ch):
                nonlocal input_bytes
                if ch in (curses.KEY_ENTER, 10, 13):
                    if self.input_channel and len(self.input) > 0:
                        if self.input[0] == '!':
                            channel, _, message = self.input[1:].partition(' ')
                            self.input_channel = channel.strip()
                            self.input = message
                        self.input = self.input.strip()
                        if len(self.input) > 0:
                            self.send(self.input_channel, self.input)
                        self.input = ""
                        self.input_position = 0
                elif ch in (curses.KEY_BACKSPACE, curses.KEY_DC, 127):
                    if len(self.input) > 0:
                        self.input = self.input[:-1]
                    if len(self.input) == 0:
                        self.input_channel = None
                elif ch == curses.KEY_LEFT:
                    self.input_position = max(self.input_position - 1, 0)
                elif ch == curses.KEY_RIGHT:
                    self.input_position = min(self.input_position + 1, len(self.input))
                elif ch > 0 and ch < 256:
                    input_bytes += ch.to_bytes(1, byteorder='big')
                    decoded = input_bytes.decode(errors='ignore')
                    if len(decoded) > 0:
                        before = self.input[:self.input_position]
                        after = self.input[self.input_position:]
                        self.input = before + decoded + after
                        self.input_position += len(decoded)
                        input_bytes = b""
                        if not self.input_channel:
                            self.input_channel = self.channel

            stdscr.timeout(GETCH_READ_TIMEOUT)
            while True:
                ch = stdscr.getch()
                with self.condition:
                    if self.stopped:
                        break
                    if ch != -1:
                        process(ch)
                        self.condition.notify()

        def input_wrapper(stdscr):
            try:
                input_main(stdscr)
            except KeyboardInterrupt:
                _thread.interrupt_main()
            except Exception as e:
                print(e)
                _thread.interrupt_main()

        def curses_wrapper():
            try:
                curses.wrapper(curses_main)
            except KeyboardInterrupt:
                _thread.interrupt_main()
            except Exception as e:
                print(e)
                _thread.interrupt_main()

        self.stopped = False
        self.curses_thread = threading.Thread(target=curses_wrapper)
        self.curses_thread.start()

    def stop(self):
        if self.curses_thread:
            with self.condition:
                self.stopped = True
                self.condition.notifyAll()
            self.curses_thread.join()
            self.curses_thread = None
