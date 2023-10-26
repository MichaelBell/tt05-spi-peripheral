import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer, ClockCycles

segments = [ 63, 6, 91, 79, 102, 109, 125, 7, 127, 103, 119, 124, 57, 94, 121, 113 ]

async def do_start(dut):
    dut._log.info("start")
    clock = Clock(dut.debug_clk, 77, units="ns")
    cocotb.start_soon(clock.start())

    dut.ena.value = 0
    dut.spi_select.value = 0
    dut.rst_n.value = 0
    await Timer(20, "ns")

    dut.ena.value = 1
    await Timer(20, "ns")

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

    #dut.debug_clk.value = 1
    #dut.debug_addr.value = 0

async def cycle_clock(dut, num=1):
    await Timer(4, "ns")
    dut.clk.value = 0
    await Timer(8, "ns")
    dut.clk.value = 1
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
    assert dut.uio_oe.value == 0b11110000
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
async def test_wrap(dut):
    await do_start(dut)

    await do_quad_write(dut, 0, [1, 0xff, 0xaa, 4, 0x80, 0x08, 0xa5, 0x5a])
    mem = [1, 0xff, 0xaa, 4, 0x80, 0x08, 0xa5, 0x5a]

    for i in range(100):
        length = random.randint(1,16)
        data = [random.randint(0,255) for _ in range(length)]
        addr = random.randint(0, 255-length)
        addr += random.randint(0, 1) * 0x200
        if random.randint(0,1) == 0:
            await do_quad_write(dut, 256+addr, data)
        else:
            await do_write(dut, 256+addr, data)
        if random.randint(0,1) == 0:
            recv = await do_quad_read(dut, 256+addr, length)
        else:
            recv = await do_read(dut, 256+addr, length)
        if length > 8: assert recv[-8:] == data[-8:]
        else: assert recv == data

        for k in range(length):
            mem[(addr + k) & 7] = data[k]
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
    data = await do_read(dut, 0x200, 128)

    # Generated with: od -Ax -tx4 -w4 tt05.bin | awk '{printf("0x%s, ", $2);}'
    expected_words = [0x21264a15, 0x21706251, 0x491462d1, 0x21026311, 0x4d136339, 0x26556829, 0x60116016, 0x21044d11, 0x4b1165b9, 0x60182001, 0x44080341, 0xd1012801, 0x44084249, 0x6cfc60d8, 0xd4f603a4, 0x60296829, 0x60116016, 0x60110a09, 0x140907c9, 0x6cfc60d9, 0xd5fc03a4, 0x0000e7e6, 0x40038000, 0x00000101, 0x10000100, 0x10000400, 0x40050050]
    expected_data = []
    for word in expected_words:
        expected_data.append(word & 0xff)
        expected_data.append((word >> 8) & 0xff)
        expected_data.append((word >> 16) & 0xff)
        expected_data.append((word >> 24) & 0xff)
    expected_data.extend([0 for _ in range(128-27*4)])
    assert len(expected_data) == 128

    for i in range(128):
        assert data[i] == expected_data[i]

    data = await do_read(dut, 0, 256)
    
    # Generated with: odod -Ax -tx4 -w4 boot2_tt05.bit | awk '{printf("0x%s, ", $2);}'
    expected_words = [0x22014b29, 0x649a02d2, 0x4a294b28, 0x2105601a, 0x64b94f28, 0x65b96539, 0x204a4d27, 0x66686628, 0x064a06be, 0x21006232, 0x03806cf8, 0x61f2d505, 0x3c010b74, 0x3101d1fd, 0x2318e7f6, 0x2200061b, 0x221f609a, 0x601a0412, 0x609a2201, 0x661d4d1b, 0x6c786619, 0xd5030380, 0x010921ab, 0xe0126619, 0x2a0e6a9a, 0x6e1ad1fc, 0x4a156e19, 0x6619661a, 0x2a0e6a9a, 0x6e1ad1fc, 0x4c126e19, 0x39016121, 0x661a1d2a, 0x6a9a6619, 0xd1fc2a0e, 0x609a2200, 0x6019490d, 0x33f4490d, 0x3bf46019, 0x2101605a, 0x490b6099, 0x00004708, 0x40008000, 0x4000f000, 0x00804020, 0x40014074, 0x4001c000, 0x02000100, 0x03000104, 0x40060000, 0x005f0300, 0x6b001218, 0x10000201]
    expected_data = []
    for word in expected_words:
        expected_data.append(word & 0xff)
        expected_data.append((word >> 8) & 0xff)
        expected_data.append((word >> 16) & 0xff)
        expected_data.append((word >> 24) & 0xff)
    expected_data.extend([0 for _ in range(256-53*4-4)])
    checksum = 0xd3536af3
    expected_data.append(checksum & 0xff)
    expected_data.append((checksum >> 8) & 0xff)
    expected_data.append((checksum >> 16) & 0xff)
    expected_data.append((checksum >> 24) & 0xff)

    assert len(expected_data) == 256

    for i in range(256):
        assert data[i] == expected_data[i]

@cocotb.test()
async def test_rosc(dut):
    await do_start(dut)
    data = await do_read(dut, 0x400, 16)

    print(data)

    assert data[0] != data[1]

