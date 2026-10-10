"""THD+N and RMS from a captured waveform (scope CSV or WAV), for test-protocol §2-§6.

Usage:
    python analysis/thd_from_capture.py capture.csv --f0 60 [--scale 10] [--load 4]
    python analysis/thd_from_capture.py capture.wav --f0 60 --scale 25.4

CSV: two columns, time (s) and voltage (V); header lines are skipped.
--scale multiplies the samples (e.g. the attenuator ratio before a sound card).
The signal is band-limited to 20 Hz-20 kHz (measurement-filter equivalent) before
THD+N is computed: everything except the fundamental bin(s), relative to total RMS.
"""
import argparse

import numpy as np


def load(path):
    if path.lower().endswith(".wav"):
        from scipy.io import wavfile
        fs, x = wavfile.read(path)
        x = x.astype(float)
        if x.ndim > 1:
            x = x[:, 0] - x[:, 1]  # differential capture: left minus right
        if np.issubdtype(type(x.flat[0]), np.integer):
            x /= np.iinfo(np.int16).max
        return fs, x
    data = np.genfromtxt(path, delimiter=",", skip_header=0, invalid_raise=False)
    data = data[~np.isnan(data).any(axis=1)]
    t, x = data[:, 0], data[:, 1]
    return 1.0 / np.median(np.diff(t)), x


def thd_n(x, fs, f0, band=(20.0, 20e3)):
    """Return (THD+N ratio, fundamental RMS, total in-band RMS)."""
    n_per = int(round(fs / f0))
    n = (len(x) // n_per) * n_per                 # integer number of periods
    x = x[:n] - np.mean(x[:n])
    win = np.blackman(n)
    spec = np.fft.rfft(x * win)
    freqs = np.fft.rfftfreq(n, 1 / fs)
    p = np.abs(spec) ** 2
    inband = (freqs >= band[0]) & (freqs <= band[1])
    k0 = np.argmin(np.abs(freqs - f0))
    fund = np.zeros_like(p, bool)
    fund[max(k0 - 4, 0):k0 + 5] = True             # Blackman main lobe
    total = p[inband].sum()
    resid = p[inband & ~fund].sum()
    v_total = np.sqrt(np.mean(x**2))
    return np.sqrt(resid / total), v_total * np.sqrt(1 - resid / total), v_total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--f0", type=float, required=True)
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--load", type=float, default=None, help="load resistance for P_out")
    a = ap.parse_args()
    fs, x = load(a.path)
    r, v1, vt = thd_n(x * a.scale, fs, a.f0)
    print(f"fs = {fs:.0f} Hz, f0 = {a.f0} Hz, samples = {len(x)}")
    print(f"THD+N = {r*100:.3f} % ({20*np.log10(r):.1f} dB)")
    print(f"V_rms (fundamental) = {v1:.3f} V")
    if a.load:
        print(f"P_out = {v1**2 / a.load:.1f} W into {a.load} ohm")


if __name__ == "__main__":
    main()
