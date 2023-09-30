import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer, ClockCycles

segments = [ 63, 6, 91, 79, 102, 109, 125, 7, 127, 103, 119, 124, 57, 94, 121, 113 ]

async def do_start(dut):
    dut._log.info("start")
    clock = Clock(dut.debug_clk, 77, units="ns")
    cocotb.start_soon(clock.start())

    dut.spi_mosi.value = 0
    dut.spi_select.value = 1
    dut.rst_n.value = 1
    dut.clk.value = 0
    await Timer(20, "ns")

    dut.rst_n.value = 0
    await Timer(20, "ns")

    dut.rst_n.value = 1
    await Timer(20, "ns")

async def cycle_clock(dut, num=1):
    await Timer(10, "ns")
    dut.clk.value = 1
    await Timer(10, "ns")
    dut.clk.value = 0

async def do_write(dut, addr, data):
    cmd = 2
    dut.spi_select.value = 0
    for i in range(8):
        dut.spi_mosi.value = 1 if (cmd & 0x80) != 0 else 0
        cmd <<= 1
        await cycle_clock(dut)
    for i in range(24):
        dut.spi_mosi.value = 1 if (addr & 0x800000) != 0 else 0
        addr <<= 1
        await cycle_clock(dut)
    for j in range(len(data)):
        d = data[j]
        for i in range(8):
            dut.spi_mosi.value = 1 if (d & 0x80) != 0 else 0
            d <<= 1
            await cycle_clock(dut)
    dut.spi_select.value = 1
    await Timer(100, "ns")

async def do_read(dut, addr, length):
    cmd = 3
    data = []
    dut.spi_select.value = 0
    for i in range(8):
        dut.spi_mosi.value = 1 if (cmd & 0x80) != 0 else 0
        cmd <<= 1
        await cycle_clock(dut)
    for i in range(24):
        dut.spi_mosi.value = 1 if (addr & 0x800000) != 0 else 0
        addr <<= 1
        await cycle_clock(dut)
    for j in range(length):
        d = 0
        for i in range(8):
            await cycle_clock(dut)
            d <<= 1
            d |= dut.spi_miso.value
        data.append(d)
    dut.spi_select.value = 1
    await Timer(100, "ns")
    return data

@cocotb.test()
async def test_spi(dut):
    await do_start(dut)
    await do_write(dut, 1, [1, 2, 3, 4])
    recv = await do_read(dut, 1, 4)
    assert recv == [1, 2, 3, 4]

    await do_write(dut, 0, [1, 0xff, 0xaa, 4, 0x80, 0x08, 0xa5, 0x5a])
    recv = await do_read(dut, 0, 8)
    assert recv == [1, 0xff, 0xaa, 4, 0x80, 0x08, 0xa5, 0x5a]

    for i in range(100):
        length = random.randint(1,8)
        data = [random.randint(0,255) for _ in range(length)]
        addr = random.randint(0, 8-length)
        await do_write(dut, addr, data)
        recv = await do_read(dut, addr, length)
        assert recv == data

@cocotb.test()
async def test_debug(dut):
    await do_start(dut)
    await do_write(dut, 0, [1, 2, 3, 4, 5, 6, 7, 8])

    await FallingEdge(dut.debug_clk)
    for i in range(8):
        dut.debug_addr.value = i*2
        await ClockCycles(dut.debug_clk, 1, False)
        assert dut.debug_data.value == i + 1
        assert dut.segments.value == segments[i+1]

    for j in range(10):
        data = [random.randint(0,255) for _ in range(8)]
        await do_write(dut, 0, data)

        await FallingEdge(dut.debug_clk)
        for i in range(16):
            dut.debug_addr.value = i
            await ClockCycles(dut.debug_clk, 1, False)
            nibble = (data[i >> 1] >> (4 * (i & 1))) & 0xF
            assert dut.debug_data.value == nibble
            assert dut.segments.value == segments[nibble]
