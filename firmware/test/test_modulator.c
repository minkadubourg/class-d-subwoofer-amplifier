/* Host-side tests for the modulator arithmetic: build with `make -C firmware test`. */
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#include "amp_config.h"
#include "modulator.h"

#define FS 400000.0

static void check_timing_invariants(uint32_t c)
{
    uint32_t ccr_hi_a = c - DEAD_HALF, ccr_lo_a = c + DEAD_HALF;
    uint32_t cb = PWM_ARR - c;
    uint32_t ccr_hi_b = cb - DEAD_HALF, ccr_lo_b = cb + DEAD_HALF;
    /* dead time on every transition: exactly 2 * DEAD_HALF counts */
    assert(ccr_lo_a - ccr_hi_a == 2 * DEAD_HALF);
    assert(ccr_lo_b - ccr_hi_b == 2 * DEAD_HALF);
    /* every switch keeps its minimum on-time */
    assert(ccr_hi_a >= MIN_ON && ccr_hi_b >= MIN_ON);
    assert(PWM_ARR - ccr_lo_a >= MIN_ON && PWM_ARR - ccr_lo_b >= MIN_ON);
}

int main(int argc, char **argv)
{
    modulator_t m;

    /* 1. Silence at any DC offset settles to 50 % (zero differential voltage). */
    modulator_reset(&m, 2048);
    uint32_t c = 0;
    for (int i = 0; i < 2000000; i++) c = modulator_step(&m, 1862);   /* 1.5 V offset */
    assert(c == PWM_ARR / 2);

    /* 2. Timing invariants hold for any input, including full-scale steps and clipping. */
    srand(1);
    for (int i = 0; i < 1000000; i++) {
        c = modulator_step(&m, rand() % 4096);
        check_timing_invariants(c);
    }

    /* 3. A 60 Hz tone: write the duty sequence for spectral analysis. */
    modulator_reset(&m, 2048);
    for (int i = 0; i < 400000; i++)                       /* settle the DC tracker */
        modulator_step(&m, 2048 + (int)lround(1000 * sin(2 * M_PI * 60 * i / FS)));
    FILE *f = argc > 1 ? fopen(argv[1], "w") : NULL;
    double acc_re = 0, acc_im = 0;
    const int n = 400000;                                  /* 1 s = 60 periods      */
    for (int i = 0; i < n; i++) {
        double ph = 2 * M_PI * 60 * i / FS;
        int x = 2048 + (int)lround(1000 * sin(ph));
        c = modulator_step(&m, x);
        check_timing_invariants(c);
        acc_re += ((double)c - PWM_ARR / 2.0) * sin(ph);
        acc_im += ((double)c - PWM_ARR / 2.0) * cos(ph);
        if (f) fprintf(f, "%d,%u\n", x, c);
    }
    if (f) fclose(f);
    double amp = 2 * sqrt(acc_re * acc_re + acc_im * acc_im) / n;
    double expected = 1000.0 * MOD_SPAN / 2048.0;
    printf("60 Hz amplitude: %.3f counts (expected %.3f)\n", amp, expected);
    assert(fabs(amp - expected) / expected < 0.01);

    printf("all modulator tests passed\n");
    return 0;
}
