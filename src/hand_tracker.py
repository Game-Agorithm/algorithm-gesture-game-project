class LandmarkSmoother:
    def __init__(self, alpha=0.3):
        self.alpha = alpha
        self.prev_points = None

    def smooth(self, current_points):
        if not current_points:
            self.prev_points = None
            return []
        if self.prev_points is None:
            self.prev_points = current_points
            return current_points

        smoothed = []
        for (cx, cy), (px, py) in zip(current_points, self.prev_points):
            sx = self.alpha * cx + (1 - self.alpha) * px
            sy = self.alpha * cy + (1 - self.alpha) * py
            smoothed.append((sx, sy))

        self.prev_points = smoothed
        return smoothed