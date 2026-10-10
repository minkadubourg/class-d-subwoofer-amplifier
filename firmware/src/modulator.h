/* Hardware-independent modulator arithmetic (unit-tested on the host, see test/). */
#ifndef MODULATOR_H
#define MODULATOR_H
#include <stdint.h>

typedef struct {
    int32_t dc_acc;     /* DC operating point of the input, Q16 */
    int32_t shape_err;  /* noise-shaping residual, Q8           */
} modulator_t;

void modulator_reset(modulator_t *m, int32_t adc_midscale);

/* One sample: 12-bit ADC code in, leg-A switching point (timer counts) out.
 * Leg B uses PWM_ARR - c. The result is clamped so that both switches of each
 * leg keep at least MIN_ON counts of on-time around the dead-time band. */
uint32_t modulator_step(modulator_t *m, int32_t adc_code);

#endif
