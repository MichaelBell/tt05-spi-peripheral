![](../../workflows/gds/badge.svg) ![](../../workflows/docs/badge.svg) ![](../../workflows/test/badge.svg)

# SPI Peripheral

This project implements a (Q)SPI device that provides:
- 8 bytes of RAM
- A ring oscillator that works as a simple random source
- A ROM to plug into an RP2040

## Address Map

The peripheral uses 24-bit addresses for compatability, but only the bottom 11-bits are used.

| Address | Item |
| ------- | ---- |
| 0x000   | [RP2040 boot stage 2 ROM](#rp2040-boot-stage-2-rom) |
| 0x100   | [8 byte RAM](#ram) |
| 0x200   | [RP2040 program ROM](#rp2040-program-rom) |
| 0x300   | Mirror of the RAM |
| 0x400   | [Random source](#random-source) |

## Commands

The transaction format is always 8-bit command followed by 24-bit address over SPI.  Command and address are sent MSB first.  For QSPI only the data IO is done in Quad mode.

The following commands are supported:

| Command | Meaning |
| ------- | ------- |
| 0x02    | SPI Write, no delay between command and data |
| 0x03    | SPI Read, no delay between command and data |
| 0x32    | QSPI Write, no delay between command and data |
| 0x6B    | QSPI Read, 2 cycles delay between command and data |

When not in use, the 4 data lines are high-Z (inputs).  For SPI read, MISO is switched to an output one cycle before output starts.
For QSPI read all data lines are switched to outputs on the second delay cycle.  The controller should set MOSI to high-Z before the second clock edge after the last bit of the address.

## RAM

The RAM wraps every 8 bytes (the address within RAM is computed considering only the low 3 bits of the address), reads and writes are allowed to cross the wrap boundary.

If write commands are used on other parts of the address space they will instead write to the RAM.  This is untested.

## Random source

A ring oscillator provides (probably) random data in the address range 0x400-0x4FF.  This is very simple and the values may be predictable or even repeating if you happen to choose a related clock rate for the SPI access - don't use it for anything important!  Note the address selected makes no difference to the data.  Both SPI and QSPI reads are supported (all the bits in a QSPI read are generated from differently divided clocks).

# Usage with RP2040

The peripheral is designed to demonstrate various functionality when connected to the QSPI pins of an RP2040.  These pins are normally connected to a flash chip, so you will likely need a custom board to test it.

The RP2040 pin connections should be:

| TT pin | RP2040 pin |
| ------ | ---------- |
| in0    | QSPI SCK   |
| in1    | QSPI SS    |
| inout0 | QSPI D0    |
| inout1 | QSPI D1    |
| inout2 | QSPI D2    |
| inout3 | QSPI D3    |

Additionally, to test the full functionality you should have the following connections on the RP2040:

| RP2040 pin | Usage |
| ---------- | ----- |
| RUN        | Reset button (short to ground to reset) |
| GPIO 25    | LED |
| GPIO 24    | Button (short to ground when pressed) |
| GPIO 23    | Button or toggle switch (short to ground or open) |
| GPIO 20    | UART TX (unknown baud rate - use a logic analyser) |

## RP2040 boot stage 2 ROM

The RP2040 bootrom will always load the 256 bytes at address 0 into memory by using an SPI read command (03h), and then start execution at this address.

The ROM program at address 0 in this project does the following:
- Starts the peripheral clock and takes PWM, UART and GPIO out of reset.
- Sets up GPIO 23 and 24 as pulled up inputs
- Sets up GPIO 25 as an output
- Blinks the LED connected to GPIO 25 and counts the number of times the loop runs
- When the button on GPIO 24 is pressed the number of times around the blink loop is written to the 4 bytes at address 0x100 (SPI write).
- If GPIO 23 is high (not pressed):
  - The value 0xAB0 is written to the 4 bytes at address 0x104
- Else:
  - The value at address 0x104 is read and programmed as the RP2040 ROSC clock divider
  - One less than the current value is written back to address 0x104.
- The XIP controller is then set up to use QSPI reads from the SPI device and execution starts from the second ROM segment at 0x200.

The idea behind the behaviour of GPIO 23 is to allow different clock frequencies of the RP2040 (and hence the QSPI interface) to be tested.  Values of 0xab0 to 0xaa1 correspond to clock dividers of 16 to 1, which very roughly correspond to RP2040 system clock rates of 6.5MHz to 104MHz.

The SPI clock is set to system clock / 6, so at the fastest speed, QSPI reads in the next program run at around 33MHz.

Note that on the first run you should have GPIO 23 high (not pressed/connected to ground) to write the initial clock divider value.

## RP2040 program ROM

This program runs after you press the button connected to GPIO 24.  It is automatically loaded into the RP2040 XIP cache using QSPI reads and executed from there.

It does the following:
- Initializes the UART on GPIO 20
- Writes 0x55 to the UART followed by the value stored in the byte at 0x100 (the number of times the blink loop ran mod 256).  The alternating bit pattern of 0x55 should allow the UART baud rate to be established (it will vary as the RP2040 is running from its internal oscillator, and because the clock divider may have been changed above).
- Uses PWM to make the LED on GPIO 25 fade in and out.  The speed of this fade allows you to see how much faster the RP2040 is running after changing the clock divider 
- When the button on GPIO 24 is pressed, the value at 0x400 is read (and then the XIP cache for that memory address is flushed, so a different random value is read next time).
- 0x55 followed by the low 2 bytes of the value read are written to the UART.
- While GPIO 24 remains held, the LED is fully lit or extinguished depending on the value of the 8th bit of the random word.
- When GPIO 24 is released the fade cycle resumes.

# What is Tiny Tapeout?

TinyTapeout is an educational project that aims to make it easier and cheaper than ever to get your digital designs manufactured on a real chip.

To learn more and get started, visit https://tinytapeout.com.

## Verilog Projects

Edit the [info.yaml](info.yaml) and uncomment the `source_files` and `top_module` properties, and change the value of `language` to "Verilog". Add your Verilog files to the `src` folder, and list them in the `source_files` property.

The GitHub action will automatically build the ASIC files using [OpenLane](https://www.zerotoasiccourse.com/terminology/openlane/).

## How to enable the GitHub actions to build the ASIC files

Please see the instructions for:

- [Enabling GitHub Actions](https://tinytapeout.com/faq/#when-i-commit-my-change-the-gds-action-isnt-running)
- [Enabling GitHub Pages](https://tinytapeout.com/faq/#my-github-action-is-failing-on-the-pages-part)

## Resources

- [FAQ](https://tinytapeout.com/faq/)
- [Digital design lessons](https://tinytapeout.com/digital_design/)
- [Learn how semiconductors work](https://tinytapeout.com/siliwiz/)
- [Join the community](https://discord.gg/rPK2nSjxy8)

## What next?

- Submit your design to the next shuttle [on the website](https://tinytapeout.com/#submit-your-design). The closing date is **November 4th**.
- Edit this [README](README.md) and explain your design, how it works, and how to test it.
- Share your GDS on your social network of choice, tagging it #tinytapeout and linking Matt's profile:
  - LinkedIn [#tinytapeout](https://www.linkedin.com/search/results/content/?keywords=%23tinytapeout) [matt-venn](https://www.linkedin.com/in/matt-venn/)
  - Mastodon [#tinytapeout](https://chaos.social/tags/tinytapeout) [@matthewvenn](https://chaos.social/@matthewvenn)
  - Twitter [#tinytapeout](https://twitter.com/hashtag/tinytapeout?src=hashtag_click) [@matthewvenn](https://twitter.com/matthewvenn)
