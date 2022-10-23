class HSL:
    def __init__(self, hue: float, sat: float, lum: float):
        self.hue = hue
        self.sat = sat
        self.lum = lum

    def rgb(self) -> tuple[int, int, int]:
        hue = self.hue / 360.0
        sat = self.sat / 100.0
        lum = self.lum / 100.0

        if lum <= 0.5:
            b = lum * (sat + 1.0)
        else:
            b = lum + sat - lum * sat
        a = lum * 2.0 - b

        # b, r flipped in original rust port
        r = HSL.hue_to_rgb(a, b, hue + 1.0 / 3.0)
        g = HSL.hue_to_rgb(a, b, hue)
        b = HSL.hue_to_rgb(a, b, hue - 1.0 / 3.0)

        r = round(r * 255)
        g = round(g * 255)
        b = round(b * 255)
        return r, g, b

    def hue_to_rgb(a: float, b: float, hue: float) -> float:
        if hue < 0.0:
            h = hue + 1.0
        elif hue > 1.0:
            h = hue - 1.0
        else:
            h = hue

        if h < 1.0 / 6.0:
            return a + (b - a) * 6.0 * h        
        if h < 1.0 / 2.0:
            return b
        if h < 2.0 / 3.0:
            return a + (b - a) * (2.0 / 3.0 - h) * 6.0

        return a