
import wasp
import icons
import watch
import time
import fonts
import math
import machine
import ppg


# 2-bit RLE, generated from res/feet.png, 240 bytes
feet = (
    b'\x02'
    b'00'
    b'\x13\xc1-\xc4+\xc6*\xc6*\xc6&\xc3\x01\xc6\t\xc2'
    b'\x1b\xc3\x02\xc5\x08\xc4\x1a\xc4\x01\xc5\x08\xc5\x19\xc4\x02\xc3'
    b'\x08\xc6\x17\xc1\x02\xc3\x02\xc3\x08\xc6\x16\xc3\x02\xc1\x0e\xc6'
    b'\x01\xc3\x12\xc3\x11\xc6\x01\xc3\x13\xc2\x05\xc2\n\xc5\x02\xc3'
    b'\x10\xc2\x01\xc2\x02\xc6\n\xc4\x01\xc4\x10\xc2\x04\xc7\x0b\xc1'
    b'\x03\xc3\x11\xc3\x02\xc8\x10\xc2\x01\xc3\r\xc2\x02\xc9\x13\xc3'
    b'\x0b\xc1\x05\xc9\x0c\xc2\x05\xc3\x0b\xc2\x03\xc9\x0c\xc5\x03\xc2'
    b'\x0c\xc2\x02\xca\x0c\xc6\x05\xc2\t\xc2\x02\xca\x0c\xc7\x03\xc3'
    b'\r\xca\x0c\xc8\x02\xc3\x0c\xca\r\xc9\x02\xc1\r\xca\r\xc9'
    b'\x04\xc2\n\xca\x0e\xc9\x02\xc3\n\xca\x0e\xc9\x02\xc2\x0b\xca'
    b'\x0e\xca\x0e\xca\x0e\xca\x0f\xc9\x0e\xca\x0f\xca\r\xca\x0f\xca'
    b'\r\xca\x10\xcb\x0b\xca\x10\xcc\n\xca\x10\xcd\t\xca\x11\xcc'
    b'\x08\xca\x12\xcc\x07\xcb\x13\xcb\x06\xcb\x14\xcb\x05\xcc\x15\xca'
    b'\x04\xcc\x16\xc9\x05\xcc\x17\xc7\x05\xcd\x17\xc7\x05\xcc\x1a\xc4'
    b"\x07\xcb%\xca&\xca'\xc8)\xc6+\xc4\x0e"
)


class HealthApp():
    NAME = "Health"
    ICON = icons.app

    def __init__(self):
        watch.accel.reset()
        self._scroll = wasp.widgets.ScrollIndicator()
        self._wake = 0
        self._bpm = 0

    def foreground(self):
        """Cancel the alarm and draw the application.

        Cancelling the alarm has two effects. Firstly it ensures the
        step count won't change whilst we are watching it and, secondly
        it ensures that if the time of day has been set to a value in
        the past that we reconfigure the alarm.

        This does in the side effect that if the application of open at
        midnight then the reset doesn't happen for that day.
        """
        wasp.system.cancel_alarm(self._wake, self._reset)
        wasp.system.bar.clock = True
        self._page = 0
        self._draw()
        wasp.system.request_event(wasp.EventMask.SWIPE_UPDOWN)
        wasp.system.request_tick(1000)

    def background(self):
        """Set an alarm to trigger at midnight and reset the counter."""
        now = watch.rtc.get_localtime()
        yyyy = now[0]
        mm = now[1]
        dd = now[2]
        then = (yyyy, mm, dd+1, 0, 0, 0, 0, 0, 0)

        self._wake = time.mktime(then)
        wasp.system.set_alarm(self._wake, self._reset)

    def _reset(self):
        """"Reset the step counter and re-arm the alarm."""
        watch.accel.steps = 0
        self._wake += 24 * 60 * 60
        wasp.system.set_alarm(self._wake, self._reset)

    def swipe(self, event):
        if event[0] == wasp.EventType.DOWN:
            if self._page == 0:
                return
            self._page = 0
        else:
            if self._page == 1:
                return
            self._page = 1

        mute = wasp.watch.display.mute
        mute(True)
        self._draw()
        mute(False)

    def tick(self, ticks):
        t = machine.Timer(id=1, period=8000000)
        t.start()
        self._subtick(1)
        wasp.system.keep_awake()

        while t.time() < 41666:
            pass
        self._subtick(1)

        while t.time() < 83332:
            pass
        self._subtick(1)

        t.stop()
        del t

        if self._page == 0:
            self._update()

    def _subtick(self, ticks):
        """Notify the application that its periodic tick is due."""
        spl = self._hrdata.preprocess(wasp.watch.hrs.read_hrs())

        if len(self._hrdata.data) >= 240:
            self._bpm = self._hrdata.get_heart_rate()

    def _draw(self):
        """Draw the display from scratch."""
        draw = wasp.watch.drawable
        draw.fill()

        if self._page == 0:
            self._update()
            wasp.system.bar.draw()
        else:
            self._update_graph()

    def _update(self):
        draw = wasp.watch.drawable

        # Draw the icon
        draw.blit(feet, 12, 132-24)

        # Update the status bar
        now = wasp.system.bar.update()

        # Update the scroll indicator
        scroll = self._scroll
        scroll.up = False
        scroll.draw()

        # Update the step count
        count = watch.accel.steps
        t = str(count)
        w = fonts.width(fonts.sans36, t)
        draw.set_font(fonts.sans36)
        draw.set_color(draw.lighten(wasp.system.theme('spot1'), wasp.system.theme('contrast')))
        draw.string(t, 228-w, 132-18)

    def _update_graph(self):
        draw = watch.drawable
        draw.set_font(fonts.sans24)
        draw.set_color(0xffff)

        scroll = self._scroll
        scroll.down = False
        scroll.draw()
        del scroll

        o = (30, 200)

        draw.line(o[0], o[1], o[0], o[1]-150, 2, 0xffff)
        draw.line(o[0], o[1], o[0]+180, o[1], 2, 0xffff)

        steps = []

        count = watch.accel.steps
        steps.append(count)

        now = int(watch.rtc.time())
        for i in range(0, 7):
            then = now - ((24*60*60) * (-1 - i))
            data = wasp.system.steps.data(then)
            total = 0
            if data:
                for x, d in enumerate(data):
                    if d == 0 or x < 2:
                        # TODO: the x < 2 conceals BUGZ
                        continue
                    total += d
            steps.append(total)

        max_steps = max(steps + [1000])
        max_steps = math.ceil(max_steps/2000) * 2000

        steps = steps[::-1]

        space = math.floor(180 / (len(steps) + 1))
        start_p = space
        now = int(watch.rtc.time())
        for s in steps:
            line_len = int((s / max_steps) * 150)
            draw.line(o[0]+start_p, o[1]-2, o[0]+start_p, o[1]-line_len, 2, 0xffaf)
            start_p += space

        draw.set_font(fonts.sans18)
        w = int(fonts.width(fonts.sans18, "80k") / 2)
        draw.string("{}k ".format(max_steps/1000), 30 - min(w, 25), 40)

