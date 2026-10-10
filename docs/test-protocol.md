# Characterisation protocol

This protocol defines how the amplifier is evaluated against its design targets. The block-level tests are run first, so that a failure can be traced to one stage. The system-level tests then produce the figures of merit usually quoted for an audio amplifier.

| # | Metric | Target | Section |
|---|--------|--------|---------|
| 0 | Load impedance of the subwoofer, Z(f) | measured, sets the power target | [0](#0-characterise-the-load) |
| 1 | PWM carrier frequency, dead time, absence of shoot-through | 196–200 kHz, ≥ 150 ns, no current spikes | [1](#1-switching-signals-and-dead-time) |
| 2 | Maximum output power at 1 % THD+N | 1.7 kW into the subwoofer impedance | [2](#2-maximum-output-power) |
| 3 | Efficiency η(P_out) | > 90 % at rated power | [3](#3-efficiency) |
| 4 | THD+N vs output power and vs frequency | < 1 % up to rated power, 20–200 Hz | [4](#4-thdn) |
| 5 | Frequency response (−3 dB band) | flat ±1 dB over 20–200 Hz | [5](#5-frequency-response) |
| 6 | Residual noise and dynamic range (A-weighted) | recorded | [6](#6-residual-noise-and-dynamic-range) |
| 7 | Switching residual at the output | ≥ 40 dB below the 196 kHz carrier at the bridge | [7](#7-switching-residual) |
| 8 | Power-supply rejection (PSRR) | recorded at 100 Hz and 1 kHz | [8](#8-power-supply-rejection) |
| 9 | Output DC offset and turn-on transient | < 50 mV, no audible pop | [9](#9-dc-offset-and-turn-on) |
| 10 | Thermal steady state at 1/8 rated power | T_J < 150 °C, estimated from the heatsink temperature | [10](#10-thermal-steady-state) |
| 11 | Listening test on the subwoofer | stable playback at event level for 1 h | [11](#11-system-test-on-the-subwoofer) |

## Equipment

- Bench DC supply, current-limited, 0–100 V (or two supplies in series), with a fuse in series with the rail.
- **Non-inductive power resistors as dummy load**: 4 Ω and 8 Ω, rated for the test power. At full power, 1.7 kW of heat needs a water- or fan-cooled load bank. Use a short burst (see §2) if one is not available.
- Oscilloscope with a **differential probe**, or two channels in A−B mode with matched probes. The output is bridged (BTL): neither output terminal is ground.
- Function generator. An audio analyzer is ideal. If none is available, use a PC sound card behind a resistive divider and an isolation transformer, with the analysis scripts in [`analysis/`](../analysis).
- True-RMS multimeter, DC current shunt or clamp meter, and a thermocouple or IR thermometer.
- Measurement low-pass filter for audio measurements: 20 kHz, AES17-style. A class-D output must not be fed directly to an analyzer, because the 196 kHz residual corrupts THD+N readings.

## Safety

- **Ramp the rail.** Bring the board up at 12 V, then 24 V, 48 V and finally 100 V, and repeat tests 1 and 9 at each step. Keep the supply current-limited until test 1 passes at 100 V.
- Never connect a grounded scope probe to an output terminal. With a bridged output, that shorts one half-bridge to ground.
- Disconnect the subwoofer for every test except 11. Use the dummy load.
- Above 50 V DC, treat the board as hazardous: no touching while powered, and discharge the bulk capacitors before rewiring.

## 0. Characterise the load

The power target depends on the load impedance, since P = V_bus² / 2R at full modulation. On a 100 V rail, 1.7 kW requires R ≤ 2.94 Ω.

1. Measure the voice-coil DC resistance R_e with a multimeter.
2. Sweep the impedance from 10 Hz to 1 kHz. Use a sine through a known series resistor, or an impedance jig with REW. Record |Z(f)|, the resonance frequency f_s and the minimum impedance in the 20–200 Hz band.
3. Use the minimum in-band impedance as the design load for tests 2–4.

## 1. Switching signals and dead time

1. With the bridge unpowered (gate drivers powered only), capture all four gate signals (CH1, CH1N, CH2, CH2N) with the input at mid-scale.
2. Check the carrier frequency (196–200 kHz) and the 50 % duty cycle at zero input.
3. Measure the dead time at both edges of each leg, from 10 % of the falling gate to 10 % of the rising gate. It must be ≥ 150 ns and symmetric.
4. Power the rail at 12 V into the dummy load. Watch the rail current with the current probe. Short spikes at every edge mean shoot-through: increase the dead time.
5. Record the switch-node waveforms. Note the ringing frequency and amplitude, which come from layout parasitics. Overshoot must stay well below the MOSFET's 650 V rating.

## 2. Maximum output power

1. Drive a 60 Hz sine at increasing amplitude into the design load (test 0).
2. Measure the output with the differential probe after the LC filter. Record V_rms and THD+N at each step.
3. Report P_out = V_rms² / R at the point where THD+N reaches 1 %, and again at 10 %.
4. **Burst method** if the load bank cannot absorb continuous power: send 20 cycles at 60 Hz, then 480 ms off (about a 4 % duty cycle). Report the burst power, and note that the thermal limit (test 10) is a separate question.

## 3. Efficiency

1. Measure the DC input power P_in = V_bus · I_bus, with the voltage at the board terminals and a true-DC current measurement.
2. Measure the output power P_out after the filter, with a true-RMS meter or the scope's RMS measurement over an integer number of periods.
3. Compute η = P_out / P_in at about 10 points from 1 W to the maximum power, at 60 Hz.
4. Also record the idle power (zero input) and the gate-driver supply power separately.
5. Plot η against P_out next to the model in [`analysis/power_stage.py`](../analysis/power_stage.py). Use the gap to calibrate the switching-loss terms, which the datasheet only gives at 400 V and 20 A.

## 4. THD+N

1. Feed the output through the 20 kHz measurement filter and an attenuator to the analyzer or sound card.
2. Measure THD+N against output power at 60 Hz, from 1 W to the 10 % point. Use a log sweep.
3. Measure THD+N against frequency at 1/8 rated power: 20, 30, 40, 60, 80, 100, 150 and 200 Hz.
4. Repeat test 2 for three dead times (for example 100, 150 and 200 ns). Compare with the open-loop prediction in [`figures/deadtime_thd.png`](../figures/deadtime_thd.png): the error term 2·f_sw·t_dead·V_bus should dominate at low power.

## 5. Frequency response

1. At 1 W into the design load, sweep 10 Hz to 20 kHz with a constant input amplitude.
2. Plot the gain relative to the 60 Hz gain. Report the −3 dB points and the ripple over 20–200 Hz.
3. Repeat with the subwoofer connected, at low level, to see the filter's interaction with the real load impedance.

## 6. Residual noise and dynamic range

1. Short the input (or terminate it with the source impedance) and measure the output noise in a 20 Hz–20 kHz band, both unweighted and A-weighted.
2. Report the dynamic range: 20·log10(V_out,max,rms / V_noise,rms), with V_out,max taken at 1 % THD+N.

## 7. Switching residual

1. Without the measurement filter, measure the 196 kHz component at the load with the differential probe. Use the scope's FFT.
2. Compare it with the bridge-side amplitude to get the filter attenuation. Check it against [`figures/output_filter.png`](../figures/output_filter.png).

## 8. Power-supply rejection

1. With zero input, add a known ripple to the rail. Use a series transformer winding, or measure the rail's own 100 Hz ripple if it uses a rectified supply.
2. Measure the same frequency at the output. PSRR = 20·log10(V_ripple,rail / V_ripple,out).
3. Repeat at 1 kHz. Without feedback, expect poor PSRR, since the output scales directly with V_bus. This motivates closed-loop control.

## 9. DC offset and turn-on

1. With zero input, measure the DC voltage across the load. It must be < 50 mV.
2. Capture the load voltage during power-up and power-down. Record the peak transient. The gate drive must stay disabled until the rail and the ADC reference have settled.

## 10. Thermal steady state

1. Drive the dummy load at 1/8 of rated power with pink noise (or a 60 Hz sine as a conservative stand-in) for 1 hour.
2. Log the heatsink temperature at the MOSFET tab every 5 minutes, along with the ambient temperature.
3. Estimate the junction temperature: T_J ≈ T_tab + P_device · R_θJC, with P_device from test 3's loss measurement divided by 4.
4. Pass if T_J < 150 °C at the maximum expected ambient (45 °C). Correct the measurement by (45 − T_ambient).

## 11. System test on the subwoofer

1. Connect the subwoofer and play program material at increasing level, up to the level needed at an event.
2. Hold that level for 1 hour while monitoring the heatsink temperature and rail current.
3. Report any protection trips, audible distortion, or thermal drift.

## Results table

| Test | Condition | Result | Target met |
|------|-----------|--------|-----------|
| 0 | R_e, f_s, Z_min (20–200 Hz) | | |
| 1 | f_sw, t_dead, shoot-through | | |
| 2 | P_out @ 1 % / 10 % THD+N, 60 Hz | | |
| 3 | η at 1/8 and full power | | |
| 4 | THD+N @ 1/8 power, 60 Hz | | |
| 5 | −3 dB band | | |
| 6 | Noise (A-wtd), dynamic range | | |
| 7 | 196 kHz residual at load | | |
| 8 | PSRR @ 100 Hz | | |
| 9 | DC offset, turn-on peak | | |
| 10 | T_tab, estimated T_J after 1 h | | |
| 11 | 1 h playback on the subwoofer | | |
