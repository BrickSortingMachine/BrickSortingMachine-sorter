import enum


class TimerState(enum.Enum):
    PAUSED = 0
    RUNNING = 1


class StateTimer:
    def __init__(self) -> None:
        self.accumulated_seconds = 0
        self.last_start = None
        self.state = TimerState.PAUSED

    def resume(self, dt_now):
        if self.state == TimerState.PAUSED:
            self.state = TimerState.RUNNING
            self.last_start = dt_now

    def pause(self, dt_now):
        if self.state == TimerState.RUNNING:
            self.state = TimerState.PAUSED
            self.accumulated_seconds += (dt_now - self.last_start).total_seconds()
            self.last_start = None

    def reset(self):
        self.state = TimerState.PAUSED
        self.accumulated_seconds = 0
        self.last_start = None

    def get_seconds(self, dt_now):
        if self.state == TimerState.PAUSED:
            return self.accumulated_seconds
        elif self.state == TimerState.RUNNING:
            return self.accumulated_seconds + (dt_now - self.last_start).total_seconds()
