import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer, ClockCycles

segments = [ 63, 6, 91, 79, 102, 109, 125, 7, 127, 103, 119, 124, 57, 94, 121, 113 ]

async def do_start(dut):
    dut._log.info("start")
    clock = Clock(dut.debug_clk, 77, units="ns")
    cocotb.start_soon(clock.start())

    dut.spi_select.value = 1
    dut.rst_n.value = 1
    dut.clk.value = 0
    await Timer(20, "ns")

    dut.rst_n.value = 0
    await Timer(20, "ns")

    dut.rst_n.value = 1
    await Timer(20, "ns")
    assert dut.uio_oe.value == 0b11110000
    dut.spi_mosi.value = 0
    await Timer(20, "ns")

async def cycle_clock(dut, num=1):
    await Timer(4, "ns")
    dut.clk.value = 1
    await Timer(8, "ns")
    dut.clk.value = 0
    await Timer(5, "ns")

async def do_write(dut, addr, data):
    assert dut.uio_oe.value == 0b11110000
    cmd = 2
    dut.spi_select.value = 0
    await Timer(10, "ns")
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
        assert dut.uio_oe.value == 0b11110000
        for i in range(8):
            dut.spi_mosi.value = 1 if (d & 0x80) != 0 else 0
            d <<= 1
            await cycle_clock(dut)
    dut.spi_select.value = 1
    await Timer(100, "ns")

async def do_read(dut, addr, length):
    assert dut.uio_oe.value == 0b11110000
    cmd = 3
    data = []
    dut.spi_select.value = 0
    await Timer(10, "ns")
    for i in range(8):
        dut.spi_mosi.value = 1 if (cmd & 0x80) != 0 else 0
        cmd <<= 1
        await cycle_clock(dut)
    for i in range(24):
        dut.spi_mosi.value = 1 if (addr & 0x800000) != 0 else 0
        addr <<= 1
        if (i == 23):
            assert dut.uio_oe.value == 0b11110010
        else:
            assert dut.uio_oe.value == 0b11110000
        await cycle_clock(dut)
    for j in range(length):
        d = 0
        assert dut.uio_oe.value == 0b11110010
        for i in range(8):
            d <<= 1
            d |= dut.spi_miso.value
            await cycle_clock(dut)
        data.append(d)
    dut.spi_select.value = 1
    await Timer(10, "ns")
    assert dut.uio_oe.value == 0b11110000
    await Timer(90, "ns")
    return data

async def do_quad_read(dut, addr, length):
    assert dut.uio_oe.value == 0b11110000
    cmd = 0x6B
    data = []
    dut.spi_select.value = 0
    await Timer(10, "ns")
    for i in range(8):
        dut.spi_mosi.value = 1 if (cmd & 0x80) != 0 else 0
        cmd <<= 1
        await cycle_clock(dut)
    for i in range(24):
        dut.spi_mosi.value = 1 if (addr & 0x800000) != 0 else 0
        addr <<= 1
        await cycle_clock(dut)
    assert dut.uio_oe.value == 0b11110000
    await cycle_clock(dut)
    assert dut.uio_oe.value == 0b11111111
    await cycle_clock(dut)
    for j in range(length):
        d = 0
        assert dut.uio_oe.value == 0b11111111
        for i in range(2):
            d <<= 4
            d |= dut.spi_q_data_out.value
            await cycle_clock(dut)
        data.append(d)
    dut.spi_select.value = 1
    await Timer(10, "ns")
    assert dut.uio_oe.value == 0b11110000
    await Timer(90, "ns")
    return data

async def do_quad_write(dut, addr, data):
    assert dut.uio_oe.value == 0b11110000
    cmd = 0x32
    dut.spi_select.value = 0
    await Timer(10, "ns")
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
        assert dut.uio_oe.value == 0b11110000
        for i in range(2):
            dut.spi_mosi.value = 1 if (d & 0x10) != 0 else 0
            dut.uio_in.value = (d & 0xe0) >> 5
            d <<= 4
            await cycle_clock(dut)
    dut.spi_select.value = 1
    await Timer(100, "ns")

@cocotb.test()
async def test_spi(dut):
    await do_start(dut)
    await do_write(dut, 1, [1, 2, 3, 4])
    recv = await do_read(dut, 257, 4)
    assert recv == [1, 2, 3, 4]

    await do_write(dut, 0, [1, 0xff, 0xaa, 4, 0x80, 0x08, 0xa5, 0x5a])
    recv = await do_read(dut, 256, 8)
    assert recv == [1, 0xff, 0xaa, 4, 0x80, 0x08, 0xa5, 0x5a]

    mem = recv
    for i in range(100):
        length = random.randint(1,8)
        data = [random.randint(0,255) for _ in range(length)]
        addr = random.randint(0, 8-length)
        await do_write(dut, 256+addr, data)
        recv = await do_read(dut, 256+addr, length)
        assert recv == data

        for k in range(length):
            mem[addr + k] = data[k]
        recv = await do_read(dut, 256, 8)
        assert recv == mem

@cocotb.test()
async def test_quad_spi(dut):
    await do_start(dut)
    await do_quad_write(dut, 1, [1, 2, 3, 4])
    recv = await do_quad_read(dut, 257, 4)
    assert recv == [1, 2, 3, 4]

    await do_quad_write(dut, 0, [1, 0xff, 0xaa, 4, 0x80, 0x08, 0xa5, 0x5a])
    recv = await do_quad_read(dut, 256, 8)
    assert recv == [1, 0xff, 0xaa, 4, 0x80, 0x08, 0xa5, 0x5a]

    mem = recv
    for i in range(100):
        length = random.randint(1,8)
        data = [random.randint(0,255) for _ in range(length)]
        addr = random.randint(0, 8-length)
        await do_quad_write(dut, 256+addr, data)
        recv = await do_quad_read(dut, 256+addr, length)
        assert recv == data

        for k in range(length):
            mem[addr + k] = data[k]
        recv = await do_quad_read(dut, 256, 8)
        assert recv == mem

@cocotb.test()
async def test_mix(dut):
    await do_start(dut)

    await do_quad_write(dut, 0, [1, 0xff, 0xaa, 4, 0x80, 0x08, 0xa5, 0x5a])
    mem = [1, 0xff, 0xaa, 4, 0x80, 0x08, 0xa5, 0x5a]

    for i in range(100):
        length = random.randint(1,8)
        data = [random.randint(0,255) for _ in range(length)]
        addr = random.randint(0, 8-length)
        if random.randint(0,1) == 0:
            await do_quad_write(dut, 256+addr, data)
        else:
            await do_write(dut, 256+addr, data)
        if random.randint(0,1) == 0:
            recv = await do_quad_read(dut, 256+addr, length)
        else:
            recv = await do_read(dut, 256+addr, length)
        assert recv == data

        for k in range(length):
            mem[addr + k] = data[k]
        if random.randint(0,1) == 0:
            recv = await do_quad_read(dut, 256, 8)
        else:
            recv = await do_read(dut, 256, 8)
        assert recv == mem

@cocotb.test()
async def test_debug(dut):
    await do_start(dut)
    await do_write(dut, 0, [1, 2, 3, 4, 5, 6, 7, 8])

    DEBUG_BYTES = 8

    await FallingEdge(dut.debug_clk)
    for i in range(DEBUG_BYTES):
        dut.debug_addr.value = i*2
        await ClockCycles(dut.debug_clk, 1, False)
        assert dut.debug_data.value == i + 1
        assert dut.segments.value == segments[i+1]

    for j in range(10):
        data = [random.randint(0,255) for _ in range(8)]
        await do_write(dut, 0, data)

        await FallingEdge(dut.debug_clk)
        for i in range(DEBUG_BYTES*2):
            dut.debug_addr.value = i
            await ClockCycles(dut.debug_clk, 1, False)
            nibble = (data[i >> 1] >> (4 * (i & 1))) & 0xF
            assert dut.debug_data.value == nibble
            assert dut.segments.value == segments[nibble]

@cocotb.test()
async def test_rom(dut):
    await do_start(dut)
    data = await do_read(dut, 0, 256)

    expected_words = [0x4a084b07, 0x2104601a, 0x4b0762d1, 0x60182001, 0x18400341, 0xd1012801, 0x18404249, 0xe7f860d8, 0x4000f000, 0x400140a0, 0x40050050]
    expected_data = []
    for word in expected_words:
        expected_data.append(word & 0xff)
        expected_data.append((word >> 8) & 0xff)
        expected_data.append((word >> 16) & 0xff)
        expected_data.append((word >> 24) & 0xff)
    expected_data.extend([0 for _ in range(208)])
    expected_data.append(0x5a)
    expected_data.append(0xa2)
    expected_data.append(0x46)
    expected_data.append(0x16)

    assert len(expected_data) == 256
    assert expected_data[43] == 0x40
    assert expected_data[255] == 0x16

    for i in range(256):
        assert data[i] == expected_data[i]