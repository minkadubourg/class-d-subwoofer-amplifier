"""Render the analysis figures used in the README and report."""
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
import power_stage as ps  # noqa: E402
import pwm_sim as sim  # noqa: E402

FIG = os.path.join(HERE, "..", "figures")
os.makedirs(FIG, exist_ok=True)
C1, C2, C3, C4 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
INK, MUTED, GRID = "#1f1f1e", "#6b6a64", "#e6e5e0"
plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED,
    "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.8, "lines.linewidth": 2, "legend.frameon": False,
    "figure.dpi": 150, "savefig.bbox": "tight",
})
R_TARGET = 100.0**2 / (2 * 1700.0)  # load giving 1.7 kW at 100 V


def save(fig, name):
    fig.savefig(os.path.join(FIG, name))
    plt.close(fig)


# 1. Power budget: efficiency and per-device dissipation vs output power
p = np.logspace(np.log10(10), np.log10(1700), 200)
eta, p_stage = ps.efficiency(p, R_TARGET)
eta_hi, p_stage_hi = ps.efficiency(p, R_TARGET, qrr_scales=False)
fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.6))
a.fill_between(p, eta_hi * 100, eta * 100, color="#cde2fb", lw=0)
a.plot(p, eta * 100, color=C1)
a.text(15, 80, "band: Qrr constant\n(conservative bound)", fontsize=8, color=MUTED)
a.set(xscale="log", xlabel="output power (W)", ylabel="efficiency (%)", ylim=(0, 100),
      title=f"Efficiency into {R_TARGET:.2f} Ω (model)")
b.fill_between(p, p_stage / 4, p_stage_hi / 4, color="#fbd9c9", lw=0)
b.plot(p, p_stage / 4, color=C2, label="dissipation per MOSFET")
lim = ps.max_device_dissipation(7.0)
b.axhline(lim, color=MUTED, ls="--", lw=1)
b.text(12, lim * 1.08, f"limit with 7 °C/W heatsink ({lim:.1f} W)", color=MUTED, fontsize=8)
for pp, lab in ((1700 / 8, "1/8 power"), (1700, "full power")):
    b.axvline(pp, color=GRID, lw=1)
    b.text(pp * 0.93, 30, lab, rotation=90, va="center", ha="right", fontsize=8, color=MUTED)
b.set(xscale="log", xlabel="output power (W)", ylabel="W per device", ylim=(0, 48),
      title="Thermal budget (model)")
for ax in (a, b):
    ax.title.set_color(INK); ax.title.set_fontsize(10)
save(fig, "power_budget.png")

# 2. Loss breakdown at 1/8 and full power
names = ["conduction", "switching (V-I overlap)", "body-diode recovery", "Coss", "dead-time diode"]
cols = [C1, C2, C3, C4, MUTED]
fig, ax = plt.subplots(figsize=(8, 2.6))
for row, (pp, lab) in enumerate(((1700 / 8, "1/8 power (212 W)"), (1700, "full power (1.7 kW)"))):
    l = ps.losses(pp, R_TARGET)
    left = 0
    for n, c in zip(names, cols):
        w = float(l[n])
        ax.barh(row, w, left=left, color=c, edgecolor="white", linewidth=2, height=0.55,
                label=n if row == 0 else None)
        left += w
    ax.text(left + 2, row, f"{left:.0f} W", va="center", fontsize=9, color=INK)
ax.set_yticks([0, 1], ["1/8 power (212 W)", "full power (1.7 kW)"])
ax.set_xlabel("stage loss (W, model)")
ax.grid(axis="y", visible=False)
ax.legend(ncol=3, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.38))
save(fig, "loss_breakdown.png")

# 3. Output filter: values as annotated vs. likely intended vs. Butterworth design
f = np.logspace(1, np.log10(1e6), 600)
R = 4.0
Lb, Cb = sim.butterworth_lc(R, 20e3)
fig, ax = plt.subplots(figsize=(8, 3.8))
for (L, C, lab, c, ls) in ((100e-3, 470e-9, "as annotated: 100 mH, 470 nF", C2, "-"),
                           (100e-6, 470e-9, "100 µH, 470 nF (likely intended)", C4, "-"),
                           (Lb, Cb, f"Butterworth 20 kHz: {Lb*1e6:.1f} µH, {Cb*1e6:.2f} µF", C1, "-")):
    ax.plot(f, sim.gain_db(*sim.lc_differential(L, C, R), f), color=c, ls=ls, label=lab)
ax.axvspan(20, 200, color="#cde2fb", alpha=0.6, lw=0)
ax.text(63, 10, "subwoofer band", ha="center", fontsize=8, color=MUTED)
ax.axvline(sim.F_SW, color=MUTED, lw=1, ls="--")
ax.text(sim.F_SW * 1.08, 5, "f_sw = 196 kHz", fontsize=8, color=MUTED)
ax.set(xscale="log", ylim=(-160, 20), xlabel="frequency (Hz)", ylabel="gain (dB)",
       title="Output filter into a 4 Ω load (per-side L and C)")
ax.title.set_color(INK); ax.title.set_fontsize(10)
ax.legend(loc="lower left", fontsize=8)
save(fig, "output_filter.png")

# 4. Dead-time distortion (averaged model, 60 Hz, Butterworth filter, 4 ohm)
tds = np.array([0, 25, 50, 75, 100, 150, 200]) * 1e-9
fig, ax = plt.subplots(figsize=(8, 3.6))
for amp, c in ((0.9, C1), (0.35, C2), (0.1, C3)):
    vals = []
    for td in tds:
        t, v = sim.simulate(60.0, amp, R, Lb, Cb, td)
        vals.append(sim.thd(v, t[1] - t[0], 60.0) * 100)
    pout = (amp * 100) ** 2 / (2 * R)
    ax.plot(tds * 1e9, vals, "o-", color=c, ms=5, label=f"m = {amp} ({pout:.0f} W)")
ax.set(xlabel="dead time (ns)", ylabel="THD (%)", title="Open-loop dead-time distortion at 60 Hz (simulated)")
ax.title.set_color(INK); ax.title.set_fontsize(10)
ax.legend(fontsize=8)
save(fig, "deadtime_thd.png")

# 5. Rail-limited power vs load impedance
r = np.linspace(1.5, 8.5, 200)
fig, ax = plt.subplots(figsize=(6.5, 3.2))
ax.plot(r, ps.max_sine_power(100, r), color=C1)
ax.axhline(1700, color=C2, lw=1, ls="--")
ax.text(6.2, 1780, "1.7 kW target", color=C2, fontsize=8)
for rr in (2.0, 4.0, 8.0):
    ax.plot(rr, ps.max_sine_power(100, rr), "o", color=C1, ms=5)
    ax.annotate(f"{ps.max_sine_power(100, rr):.0f} W", (rr, ps.max_sine_power(100, rr)),
                xytext=(6, 4), textcoords="offset points", fontsize=8, color=INK)
ax.set(xlabel="load impedance (Ω)", ylabel="max sine power (W)",
       title="Full bridge on a 100 V rail: P = V² / 2R")
ax.title.set_color(INK); ax.title.set_fontsize(10)
save(fig, "rail_power.png")
print("figures written")
