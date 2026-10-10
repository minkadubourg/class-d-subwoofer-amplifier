"""Behavioural simulation of the full-bridge stage: AD-mode PWM, dead time, LC filter.

Two models are used:
* a switching-cycle-averaged model for distortion: each PWM period applies
  v = m(t) V_bus - 2 V_bus f_sw t_dead sign(i), the standard dead-time error of a
  full bridge, to the output filter and load;
* the exact linear transfer function of the LC filter for switching-ripple attenuation.
"""
import numpy as np

V_BUS = 100.0
F_SW = 196e3


def lc_differential(L_side, C_side, R):
    """H(s) = v_load / v_bridge for one series L and one shunt C per side and a load R
    across the two outputs. Differential equivalent: 2L in series, C/2 across R."""
    L, C = 2 * L_side, C_side / 2
    num = [1.0]
    den = [L * C, L / R, 1.0]
    return num, den


def gain_db(num, den, f):
    s = 2j * np.pi * np.asarray(f)
    return 20 * np.log10(np.abs(np.polyval(num, s) / np.polyval(den, s)))


def butterworth_lc(R, fc):
    """Per-side L and C giving a 2nd-order Butterworth response into load R."""
    w = 2 * np.pi * fc
    L = R / (np.sqrt(2) * w) / 2 * 2  # differential 2L = R*sqrt(2)/w  -> L_side = R/(sqrt(2) w)
    L_side = R / (np.sqrt(2) * w)
    C_diff = 1 / (np.sqrt(2) * w * R)
    return L_side, 2 * C_diff


def simulate(f_sig, amplitude, R, L_side, C_side, t_dead, cycles=12, steps_per_period=8):
    """Averaged model integrated at steps_per_period samples per PWM period (RK4).
    Returns t, load voltage (last 10 signal cycles)."""
    L, C = 2 * L_side, C_side / 2
    dt = 1.0 / (F_SW * steps_per_period)
    n = int(cycles / f_sig / dt)
    t = np.arange(n) * dt
    m = amplitude * np.sin(2 * np.pi * f_sig * t)
    dv = 2 * V_BUS * F_SW * t_dead
    i, v = 0.0, 0.0
    out = np.empty(n)

    def f(i, v, mk):
        vb = mk * V_BUS - dv * np.tanh(i / 0.05)  # smooth sign, 50 mA width
        return (vb - v) / L, (i - v / R) / C

    for k in range(n):
        mk = m[k]
        a1, b1 = f(i, v, mk)
        a2, b2 = f(i + dt / 2 * a1, v + dt / 2 * b1, mk)
        a3, b3 = f(i + dt / 2 * a2, v + dt / 2 * b2, mk)
        a4, b4 = f(i + dt * a3, v + dt * b3, mk)
        i += dt / 6 * (a1 + 2 * a2 + 2 * a3 + a4)
        v += dt / 6 * (b1 + 2 * b2 + 2 * b3 + b4)
        out[k] = v
    keep = t >= (cycles - 10) / f_sig
    return t[keep], out[keep]


def thd(signal, dt, f0, n_harm=10):
    """THD from an integer number of periods using a Hann-free exact-bin FFT."""
    spec = np.abs(np.fft.rfft(signal)) / len(signal)
    freqs = np.fft.rfftfreq(len(signal), dt)
    def amp(f):
        return spec[np.argmin(np.abs(freqs - f))]
    fund = amp(f0)
    harm = np.sqrt(sum(amp(k * f0) ** 2 for k in range(2, n_harm + 1)))
    return harm / fund


if __name__ == "__main__":
    R = 4.0
    print("As drawn (100 mH, 470 nF):", round(1 / (2 * np.pi * np.sqrt(2 * 100e-3 * 470e-9 / 2))), "Hz cut-off")
    Ls, Cs = butterworth_lc(R, 20e3)
    print(f"Butterworth 20 kHz into {R} ohm: L = {Ls*1e6:.1f} uH per side, C = {Cs*1e6:.2f} uF per side")
    for td in (0, 50e-9, 150e-9, 300e-9):
        t, v = simulate(60.0, 0.35, R, Ls, Cs, td)
        print(f"t_dead = {td*1e9:4.0f} ns  THD = {thd(v, t[1]-t[0], 60.0)*100:.3f} %")
