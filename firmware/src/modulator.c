#include "modulator.h"
#include "amp_config.h"

void modulator_reset(modulator_t *m, int32_t adc_midscale)
{
    m->dc_acc = adc_midscale << 16;
    m->shape_err = 0;
}

uint32_t modulator_step(modulator_t *m, int32_t x)
{
    /* One-pole DC tracker (high-pass ~1 Hz at 400 kS/s). */
    m->dc_acc += ((x << 16) - m->dc_acc) >> DC_TRACK_SHIFT;
    int32_t s = x - (m->dc_acc >> 16);          /* audio, +/-2048 full scale */
    s = s * GAIN_NUM / GAIN_DEN;

    /* Target switching point in Q8 counts; first-order error feedback pushes the
     * quantisation error of the ~7.6-bit compare value above the audio band. */
    int32_t target = ((int32_t)(PWM_ARR / 2u) << 8) + ((s * (int32_t)MOD_SPAN) >> 3);
    int32_t v = target + m->shape_err;
    int32_t c = (v + 128) >> 8;
    m->shape_err = v - (c << 8);

    const int32_t lo = DEAD_HALF + MIN_ON, hi = PWM_ARR - DEAD_HALF - MIN_ON;
    if (c < lo) { c = lo; m->shape_err = 0; }
    if (c > hi) { c = hi; m->shape_err = 0; }
    return (uint32_t)c;
}
