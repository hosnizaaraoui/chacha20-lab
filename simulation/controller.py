class SimulationController:
    """Contrôleur indépendant de Qt : conserve l'index et l'historique des événements."""
    def __init__(self, events=None):
        self.events = events or []
        self.index = 0

    def set_events(self, events):
        self.events = events
        self.index = 0

    @property
    def total(self):
        return len(self.events)

    @property
    def current(self):
        return self.events[self.index] if self.events and self.index < len(self.events) else None

    def next(self):
        if self.index < len(self.events) - 1:
            self.index += 1
        return self.current

    def previous(self):
        if self.index > 0:
            self.index -= 1
        return self.current

    def seek(self, index):
        if not self.events:
            self.index = 0
            return None
        self.index = max(0, min(int(index), len(self.events) - 1))
        return self.current

    def reset(self):
        self.index = 0
        return self.current
