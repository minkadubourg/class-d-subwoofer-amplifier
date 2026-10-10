"""Loss, efficiency and thermal budget for the full-bridge power stage.

All device parameters come from the NTPF082N65S3F datasheet (onsemi, rev. 4).
This is a first-order model: it is meant to size the design and expose the
dominant loss terms, not to replace bench measurements.
"""
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Mosfet:
    name: str = "NTPF082N65S3F"
    rds_on_max_25c: float = 0.082   # ohm, VGS = 10 V
    rds_hot_factor: float = 1.5     # normalised RDS(on) at TJ = 100 C (datasheet Fig. 8)
    t_rise: float = 27e-9           # s, datasheet test conditions (400 V, 20 A, Rg = 3 ohm)
    t_fall: float = 3.7e-9          # s
    q_rr: float = 397e-9            # C, body-diode reverse-recovery charge (20 A, 100 A/us)
    e_oss_100v: float = 3.5e-6      # J, output-capacitance energy at VDS = 100 V (Fig. 11)
    q_g: float = 70e-9              # C, total gate charge at 10 V
    v_sd: float = 1.3               # V, body-diode forward voltage (max)
    r_jc: float = 2.62              # C/W, junction-to-case (TO-220 FullPAK)
    tj_max: float = 150.0           # C


@dataclass(frozen=True)
class Stage:
    v_bus: float = 100.0      # V, H-bridge supply rail
    f_sw: float = 196e3       # Hz, measured switching frequency
    t_dead: float = 150e-9    # s, dead time per transition
    v_gs: float = 10.0        # V, gate drive voltage


def max_sine_power(v_bus, r_load):
    """Undistorted sine power of a full bridge at 100 % modulation: V_bus^2 / (2 R)."""
    return v_bus**2 / (2 * r_load)


def losses(p_out, r_load, m: Mosfet = Mosfet(), s: Stage = Stage(), qrr_scales=True):
    """Total stage losses (W) by mechanism for a sine output of power p_out into r_load.

    qrr_scales: if True, the recovery charge scales with the commutated current
    (datasheet value is given at 20 A); if False, the 20 A value is used at every
    current, which is a conservative upper bound at low power."""
    i_rms = np.sqrt(p_out / r_load)
    i_avg_abs = 2 * np.sqrt(2) / np.pi * i_rms   # mean |i| of a sinusoid
    rds = m.rds_on_max_25c * m.rds_hot_factor

    # Two devices carry the load current at any time.
    conduction = 2 * i_rms**2 * rds
    # Per leg and per PWM period: one hard turn-on (V-I overlap, Coss discharge,
    # recovery of the opposite body diode) and one turn-off (V-I overlap).
    overlap = 2 * s.f_sw * 0.5 * s.v_bus * i_avg_abs * (m.t_rise + m.t_fall)
    qrr = m.q_rr * (i_avg_abs / 20.0 if qrr_scales else np.ones_like(i_rms))
    recovery = 2 * s.f_sw * qrr * s.v_bus
    coss = 2 * s.f_sw * m.e_oss_100v * np.ones_like(i_rms)
    dead_time = 2 * 2 * s.f_sw * s.t_dead * m.v_sd * i_avg_abs
    gate = 4 * m.q_g * s.v_gs * s.f_sw * np.ones_like(i_rms)  # dissipated mostly in the driver
    return {"conduction": conduction, "switching (V-I overlap)": overlap,
            "body-diode recovery": recovery, "Coss": coss, "dead-time diode": dead_time,
            "gate drive": gate}


def efficiency(p_out, r_load, **kw):
    l = losses(p_out, r_load, **kw)
    p_stage = sum(v for k, v in l.items() if k != "gate drive")
    return p_out / (p_out + p_stage), p_stage


def max_device_dissipation(r_sa, t_amb=45.0, r_cs=0.5, m: Mosfet = Mosfet()):
    """Largest per-device dissipation keeping TJ <= TJmax, one heatsink per device."""
    return (m.tj_max - t_amb) / (m.r_jc + r_cs + r_sa)


def required_heatsink(p_device, t_amb=45.0, r_cs=0.5, m: Mosfet = Mosfet()):
    """Heatsink-to-ambient resistance needed per device (negative = impossible)."""
    return (m.tj_max - t_amb) / p_device - m.r_jc - r_cs


if __name__ == "__main__":
    print("Rail-limited sine power at 100 V:")
    for r in (2.0, 2.94, 4.0, 8.0):
        print(f"  {r:4.2f} ohm -> {max_sine_power(100, r):7.0f} W")
    for p, label, q in ((1700.0, "full power", True), (1700.0 / 8, "1/8 power", True),
                        (1700.0 / 8, "1/8 power, constant Qrr (upper bound)", False)):
        eta, ps = efficiency(p, 2.94, qrr_scales=q)
        l = losses(p, 2.94, qrr_scales=q)
        print(f"\n{label}: {p:.0f} W into 2.94 ohm, efficiency {eta*100:.1f} %, stage loss {ps:.1f} W, "
              f"per device {ps/4:.1f} W, heatsink needed {required_heatsink(ps/4):.2f} C/W")
        for k, v in l.items():
            print(f"    {k:26s} {float(v):6.1f} W")
    print(f"\nAllowed per-device dissipation with the chosen 7 C/W heatsink: {max_device_dissipation(7.0):.1f} W")
