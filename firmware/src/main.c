/*
 * Class-D subwoofer amplifier: STM32L475 (B-L475E-IOT01A) modulator firmware.
 *
 * Signal chain
 *   audio -> level shifter -> PC5 / ADC1_IN14 (12 bit, triggered by TIM2)
 *         -> DC tracking -> gain -> first-order noise shaping
 *         -> TIM2 compare registers -> 4 gate signals -> gate drivers -> H-bridge
 *
 * Modulation: two-level (AD) full bridge. Leg A has duty d, leg B has duty 1 - d.
 * Each leg's high- and low-side switches get separate timer channels; the dead
 * time is created by placing their compare values DEAD_HALF counts either side of
 * the leg's switching point in centre-aligned mode:
 *
 *   counter  0 ......... c-h ..... c+h ......... ARR
 *   high     ON  ON  ON  |  off      off     off           (PWM mode 1, CCR = c - h)
 *   low      off off off    off   |  ON  ON  ON            (PWM mode 2, CCR = c + h)
 *                          <- dead ->
 *
 * Pins (Arduino header):  D1  = PA0 = TIM2_CH1 -> leg A high side
 *                         D0  = PA1 = TIM2_CH2 -> leg A low side
 *                         D10 = PA2 = TIM2_CH3 -> leg B high side
 *                         D4  = PA3 = TIM2_CH4 -> leg B low side
 *                         A0  = PC5 = ADC1_IN14 audio input
 * Fit 10 kOhm pull-downs on the four gate lines: the pins float until configured.
 *
 * Status: builds with arm-none-eabi-gcc; not yet validated on hardware.
 */
#include "stm32l4xx.h"
#include "amp_config.h"
#include "modulator.h"

static volatile uint32_t ms_ticks;
static volatile uint8_t outputs_enabled;
static modulator_t mod;

void SysTick_Handler(void) { ms_ticks++; }

static void delay_ms(uint32_t ms)
{
    uint32_t start = ms_ticks;
    while ((ms_ticks - start) < ms) { __WFI(); }
}

static void delay_cycles(uint32_t n) { while (n--) { __NOP(); } }

/* HSI16 -> PLL (x10 / 2) -> SYSCLK 80 MHz. HSI16 is factory-trimmed to +/-1 %. */
static void clock_init(void)
{
    RCC->CR |= RCC_CR_HSION;
    while (!(RCC->CR & RCC_CR_HSIRDY)) {}

    FLASH->ACR = (FLASH->ACR & ~FLASH_ACR_LATENCY) | FLASH_ACR_LATENCY_4WS
               | FLASH_ACR_PRFTEN | FLASH_ACR_ICEN | FLASH_ACR_DCEN;
    while ((FLASH->ACR & FLASH_ACR_LATENCY) != FLASH_ACR_LATENCY_4WS) {}

    RCC->CR &= ~RCC_CR_PLLON;
    while (RCC->CR & RCC_CR_PLLRDY) {}
    RCC->PLLCFGR = RCC_PLLCFGR_PLLSRC_HSI          /* 16 MHz in            */
                 | (0u << RCC_PLLCFGR_PLLM_Pos)     /* /1                   */
                 | (10u << RCC_PLLCFGR_PLLN_Pos)    /* x10 -> VCO 160 MHz   */
                 | (0u << RCC_PLLCFGR_PLLR_Pos)     /* /2  -> 80 MHz        */
                 | RCC_PLLCFGR_PLLREN;
    RCC->CR |= RCC_CR_PLLON;
    while (!(RCC->CR & RCC_CR_PLLRDY)) {}

    RCC->CFGR = (RCC->CFGR & ~RCC_CFGR_SW) | RCC_CFGR_SW_PLL;   /* AHB, APB1, APB2 /1 */
    while ((RCC->CFGR & RCC_CFGR_SWS) != RCC_CFGR_SWS_PLL) {}

    SystemCoreClock = SYSCLK_HZ;
    SysTick_Config(SYSCLK_HZ / 1000u);
}

/* Gate pins start as GPIO outputs driven low; they are switched to the timer
 * alternate function only when the modulator is running. */
static void gpio_init(void)
{
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN | RCC_AHB2ENR_GPIOCEN;
    (void)RCC->AHB2ENR;

    for (uint32_t pin = 0; pin < 4; pin++) {
        GPIOA->BSRR = (1u << (pin + 16));                                  /* low       */
        GPIOA->MODER = (GPIOA->MODER & ~(3u << (2 * pin))) | (1u << (2 * pin)); /* output */
        GPIOA->OSPEEDR |= (3u << (2 * pin));                               /* very high */
        GPIOA->AFR[0] = (GPIOA->AFR[0] & ~(0xFu << (4 * pin))) | (1u << (4 * pin)); /* AF1 = TIM2 */
    }

    GPIOC->MODER |= (3u << (2 * 5));        /* PC5 analog                         */
    GPIOC->ASCR  |= (1u << 5);              /* connect analog switch (L47x only)  */
}

static void gates_to_timer(void)
{
    for (uint32_t pin = 0; pin < 4; pin++)
        GPIOA->MODER = (GPIOA->MODER & ~(3u << (2 * pin))) | (2u << (2 * pin));
}

static void set_leg_points(uint32_t c_a, uint32_t c_b)
{
    TIM2->CCR1 = c_a - DEAD_HALF;
    TIM2->CCR2 = c_a + DEAD_HALF;
    TIM2->CCR3 = c_b - DEAD_HALF;
    TIM2->CCR4 = c_b + DEAD_HALF;
}

static void tim2_init(void)
{
    RCC->APB1ENR1 |= RCC_APB1ENR1_TIM2EN;
    (void)RCC->APB1ENR1;

    TIM2->CR1 = 0;
    TIM2->PSC = 0;
    TIM2->ARR = PWM_ARR;
    /* CH1, CH3: PWM mode 1 (high side). CH2, CH4: PWM mode 2 (low side). Preload on. */
    TIM2->CCMR1 = (6u << TIM_CCMR1_OC1M_Pos) | TIM_CCMR1_OC1PE
                | (7u << TIM_CCMR1_OC2M_Pos) | TIM_CCMR1_OC2PE;
    TIM2->CCMR2 = (6u << TIM_CCMR2_OC3M_Pos) | TIM_CCMR2_OC3PE
                | (7u << TIM_CCMR2_OC4M_Pos) | TIM_CCMR2_OC4PE;
    TIM2->CCER  = TIM_CCER_CC1E | TIM_CCER_CC2E | TIM_CCER_CC3E | TIM_CCER_CC4E;
    TIM2->CR2   = (2u << TIM_CR2_MMS_Pos);        /* TRGO on update: triggers the ADC   */

    set_leg_points(PWM_ARR / 2u, PWM_ARR / 2u);  /* 50 %: zero differential output    */
    TIM2->EGR = TIM_EGR_UG;
    /* Centre-aligned mode 1, auto-reload preload. Update (and ADC trigger) at both
     * the top and the bottom of the count: 400 kS/s, compare values reloaded there. */
    TIM2->CR1 = (1u << TIM_CR1_CMS_Pos) | TIM_CR1_ARPE;
}

static void adc_init(void)
{
    RCC->AHB2ENR |= RCC_AHB2ENR_ADCEN;
    RCC->CCIPR = (RCC->CCIPR & ~RCC_CCIPR_ADCSEL) | (3u << RCC_CCIPR_ADCSEL_Pos); /* SYSCLK */
    (void)RCC->AHB2ENR;
    ADC123_COMMON->CCR &= ~(ADC_CCR_CKMODE | ADC_CCR_PRESC);   /* asynchronous clock, /1 */

    ADC1->CR &= ~ADC_CR_DEEPPWD;
    ADC1->CR |= ADC_CR_ADVREGEN;
    delay_cycles(SYSCLK_HZ / 1000000u * 25u);   /* t_ADCVREG_STUP = 20 us               */

    ADC1->CR &= ~ADC_CR_ADCALDIF;               /* single-ended calibration             */
    ADC1->CR |= ADC_CR_ADCAL;
    while (ADC1->CR & ADC_CR_ADCAL) {}

    ADC1->SQR1  = (0u << ADC_SQR1_L_Pos) | (ADC_CHANNEL << ADC_SQR1_SQ1_Pos);
    ADC1->SMPR2 = (ADC1->SMPR2 & ~ADC_SMPR2_SMP14) | (2u << ADC_SMPR2_SMP14_Pos); /* 12.5 cyc */
    ADC1->CFGR  = ADC_CFGR_OVRMOD                        /* keep the newest sample   */
                | (1u << ADC_CFGR_EXTEN_Pos)             /* rising edge              */
                | (11u << ADC_CFGR_EXTSEL_Pos);          /* EXT11 = TIM2_TRGO        */
    ADC1->IER   = ADC_IER_EOCIE;

    ADC1->ISR = ADC_ISR_ADRDY;
    ADC1->CR |= ADC_CR_ADEN;
    while (!(ADC1->ISR & ADC_ISR_ADRDY)) {}

    NVIC_SetPriority(ADC1_2_IRQn, 0);
    NVIC_EnableIRQ(ADC1_2_IRQn);
    ADC1->CR |= ADC_CR_ADSTART;                 /* wait for TIM2 triggers               */
}

/* Runs at 400 kHz: one new duty cycle per half PWM period. */
void ADC1_2_IRQHandler(void)
{
    uint32_t c = modulator_step(&mod, (int32_t)ADC1->DR);   /* reading DR clears EOC */
    if (outputs_enabled)
        set_leg_points(c, PWM_ARR - c);
}

int main(void)
{
    clock_init();
    gpio_init();
    modulator_reset(&mod, 2048);
    tim2_init();
    adc_init();

    TIM2->CR1 |= TIM_CR1_CEN;                   /* timer runs, gates still held low      */
    delay_ms(SOFT_START_MS);

    gates_to_timer();                           /* 50 % on both legs: 0 V on the load    */
    delay_ms(10);
    outputs_enabled = 1;

    for (;;) { __WFI(); }
}
