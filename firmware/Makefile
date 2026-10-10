TARGET  = classd_amp
CC      = arm-none-eabi-gcc
OBJCOPY = arm-none-eabi-objcopy
SIZE    = arm-none-eabi-size

MCU     = -mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard
CFLAGS  = $(MCU) -DSTM32L475xx -Icmsis/core -Icmsis/device -Isrc \
          -O2 -std=c11 -Wall -Wextra -ffunction-sections -fdata-sections -g3
LDFLAGS = $(MCU) -TSTM32L475VGTX_FLASH.ld -Wl,--gc-sections -Wl,-Map=build/$(TARGET).map \
          --specs=nano.specs --specs=nosys.specs

SRCS = src/main.c src/modulator.c src/system_stm32l4xx.c src/syscalls.c startup/startup_stm32l475vgtx.s
OBJS = $(patsubst %,build/%.o,$(basename $(SRCS)))

all: build/$(TARGET).elf build/$(TARGET).bin
	$(SIZE) build/$(TARGET).elf

build/%.o: %.c
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -c $< -o $@

build/%.o: %.s
	@mkdir -p $(dir $@)
	$(CC) $(MCU) -c $< -o $@

build/$(TARGET).elf: $(OBJS)
	$(CC) $(OBJS) $(LDFLAGS) -o $@

build/$(TARGET).bin: build/$(TARGET).elf
	$(OBJCOPY) -O binary $< $@

flash: build/$(TARGET).bin
	st-flash write $< 0x08000000

clean:
	rm -rf build

.PHONY: all flash clean

# Host-side unit test of the modulator arithmetic (no hardware needed)
test:
	@mkdir -p build
	gcc -O2 -Wall -Wextra -Isrc test/test_modulator.c src/modulator.c -lm -o build/test_modulator
	./build/test_modulator build/modulator_60Hz.csv

.PHONY: test
