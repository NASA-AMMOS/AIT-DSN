from datetime import datetime
from enum import Enum

class TimerMode(Enum):
    TIMER_OFF = "TIMER_OFF"
    TIMER_RUNNING = "TIMER_RUNNING"
    TIMER_PAUSED = "TIMER_PAUSED"

class Timer(object):

    def __init__(self, *args, **kwargs):
        self.start_time = None
        self.pause_time = None
        self.expiration_time = None
        self.timer_mode = TimerMode.TIMER_OFF

    def start(self, expiration_time):
        self.expiration_time = expiration_time
        self.start_time = datetime.now()
        self.timer_mode = TimerMode.TIMER_RUNNING

    def restart(self):
        self.start(self.expiration_time)

    def cancel(self):
        self.timer_mode = TimerMode.TIMER_OFF

    def pause(self):
        if self.timer_mode == TimerMode.TIMER_RUNNING:
            self.pause_time = datetime.now()
            self.timer_mode = TimerMode.TIMER_PAUSED

    def resume(self):
        if self.timer_mode == TimerMode.TIMER_PAUSED:
            self.timer_mode = TimerMode.TIMER_RUNNING
            now = datetime.now()
            # Set the start time to account for the time elapsed before the pause
            elapsed = self.pause_time - self.start_time
            self.start_time = now - elapsed

    def expired(self):
        now = datetime.now()
        expired = False
        if self.timer_mode == TimerMode.TIMER_RUNNING:
            # Difference of datetimes returns timedelta
            # Get second difference with `.total_seconds()`
            elapsed_time = (now - self.start_time).total_seconds()
            expired = elapsed_time > self.expiration_time
        return expired

    def time_left(self):
        """Get remaining timer time"""
        if self.timer_mode == TimerMode.TIMER_RUNNING:
            now = datetime.now()
            elapsed = (now - self.start_time).total_seconds()
            # return seconds remaining, or 0 if expired
            return self.expiration_time - elapsed if elapsed < self.expiration_time else 0
        if self.timer_mode == TimerMode.TIMER_PAUSED:
            # return time between start and pause
            elapsed = (self.pause_time - self.start_time).total_seconds()
            return elapsed
        # timer is off, return 0
        return 0

