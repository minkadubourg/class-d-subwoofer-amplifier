/*
 * Class-D subwoofer amplifier: build-time configuration.
 *
 * Timing: SYSCLK = 80 MHz, TIM2 in centre-aligned mode with ARR = PWM_ARR,
 * so f_sw = 80 MHz / (2 * PWM_ARR) = 200 kHz and one timer count = 12.5 ns.
 */
#ifndef AMP_CONFIG_H
#define AMP_CONFIG_H

#define SYSCLK_HZ        80000000u
#define PWM_ARR          200u          /* f_sw = SYSCLK / (2 * ARR) = 200 kHz            */

/* Dead time: the two switches of a leg are both off while the counter is within
 * +/- DEAD_HALF counts of the leg's switching point. Each transition therefore has
 * 2 * DEAD_HALF counts of dead time: 2 * 6 * 12.5 ns = 150 ns.
 * Must exceed t_d(off) + t_f of the MOSFET plus gate-driver delay mismatch.        */
#define DEAD_HALF        6u

/* Minimum on-time kept for every switch, in counts, so that a bootstrap
 * high-side supply is refreshed every period even at full modulation.               */
#define MIN_ON           4u

/* Audio input: ADC1 channel 14 on PC5 (Arduino A0), fed by the level shifter.
 * The DC operating point is tracked by a one-pole high-pass filter, so the exact
 * level-shifter offset does not need to be calibrated.                              */
#define ADC_CHANNEL      14u
#define DC_TRACK_SHIFT   16            /* cut-off ~ f_s / (2 pi 2^16) ~ 1 Hz at 400 kS/s */

/* Modulation depth: full-scale ADC swing (+/-2048) maps to +/-MOD_SPAN counts.     */
#define MOD_SPAN         (PWM_ARR / 2u - DEAD_HALF - MIN_ON)
#define GAIN_NUM         1             /* digital volume, applied as NUM / DEN         */
#define GAIN_DEN         1

/* Soft start: outputs stay off until the DC tracker has settled.                   */
#define SOFT_START_MS    500u

#endif
