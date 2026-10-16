"""In-band SNR of the firmware modulator, with and without noise shaping.

Re-implements modulator_step() from firmware/src/modulator.c in integer
arithmetic and feeds it a 60 Hz tone sampled at 400 kS/s. Three cases:

* plain rounding of the compare value (no error feedback);
* first-order noise shaping, 12-bit input (what the firmware sees);
* first-order noise shaping, unquantised input: the shaper's own limit.

The SNR is the 60 Hz bin against everything else in 20-200 Hz, over exactly
60 periods (1 s, coherent sampling, no window).

    python analysis/noise_shaping.py
"""
import numpy as np

FS = 400_000
ARR, DEAD_HALF, MIN_ON = 200, 6, 4
MOD_SPAN = ARR // 2 - DEAD_HALF - MIN_ON
LO, HI = DEAD_HALF + MIN_ON, ARR - DEAD_HALF - MIN_ON


def modulate(x, shape=True, quantised_input=True):
    """Compare values for input samples x (ADC codes around 2048)."""
    dc, err = 2048 << 16, 0
    out = np.empty(len(x), dtype=np.int64)
    for i, xi in enumerate(x):
        if quantised_input:
            xi = int(xi)
            dc += ((xi << 16) - dc) >> 16          # one-pole DC tracker, as in firmware
            s = xi - (dc >> 16)
            target = ((ARR // 2) << 8) + ((s * MOD_SPAN) >> 3)
        else:
            target = (ARR // 2) * 256 + (xi - 2048.0) * MOD_SPAN / 8.0
        v = target + err if shape else target
        c = int(np.floor((v + 128) / 256))
        if shape:
            err = v - c * 256
        if c < LO or c > HI:
            c, err = min(max(c, LO), HI), 0
        out[i] = c
    return out


def inband_snr(c, f0=60.0, band=(20.0, 200.0)):
    p = np.abs(np.fft.rfft(c - c.mean())) ** 2
    f = np.fft.rfftfreq(len(c), 1 / FS)
    noise = (f >= band[0]) & (f <= band[1]) & (f != f0)
    return 10 * np.log10(p[f == f0].sum() / p[noise].sum())


if __name__ == "__main__":
    n = FS                                          # 1 s = 60 periods
    i = np.arange(2 * n)                            # first second settles the DC tracker
    tone = 1000 * np.sin(2 * np.pi * 60 * i / FS)
    cases = [("plain rounding, 12-bit input", 2048 + np.round(tone), False, True),
             ("noise shaping, 12-bit input", 2048 + np.round(tone), True, True),
             ("noise shaping, unquantised input", 2048 + tone, True, False)]
    for name, x, shape, q in cases:
        print(f"{name:34s} {inband_snr(modulate(x, shape, q)[n:]):6.1f} dB")
