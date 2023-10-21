// Copyright (C) 2023 Michael Bell
// SPI RAM that accepts reads and writes using commands 03h and 02h.
// Also accepts QSPI fast reads and writes using commands 6Bh and 32h.
// QSPI fast read has 2 delays cycles (or more, configurable by parameter).
// QSPI reads and writes use MOSI only for command and address, D0-D3 are used for data only.

module spi_slave #( parameter RAM_LEN_BITS = 3, parameter DEBUG_LEN_BITS = 3, FAST_READ_DELAY = 2 ) (
    input spi_clk,
    input [3:0] spi_d_in,
    input spi_select,
    output [3:0] spi_d_out,
    output reg [3:0] spi_d_oe,

    input debug_clk,
    input [DEBUG_LEN_BITS-1:0] addr_in,
    output reg [7:0] byte_out
);

    reg [30:0] cmd;
    reg [4:0] start_count;
    reg reading;
    reg writing;
    reg bad_cmd;
    reg quad;
    reg delay;

    reg [7:0] data [0:2**RAM_LEN_BITS-1];
    wire data_out;
    reg [3:0] q_data_out;
    reg [1:0] data_out_bits;

    wire spi_mosi = spi_d_in[0];
    wire spi_miso;

    always @(posedge spi_clk) begin
        if (writing) begin
            if (quad) begin
                if (cmd[2])
                    data[cmd[RAM_LEN_BITS-1+3:3]][3:0] <= spi_d_in;
                else
                    data[cmd[RAM_LEN_BITS-1+3:3]][7:4] <= spi_d_in;
            end else begin
                data[cmd[RAM_LEN_BITS-1+3:3]][7 - cmd[2:0]] <= spi_mosi;
            end
        end
    end

    wire [31:0] rp2040_rom_word = rp2040_rom(cmd[10:5]);
    wire [31:0] rp2040_rom_nibble = rp2040_rom_word >> {cmd[4:3], ~cmd[2], 2'b00};
    wire [31:0] rp2040_rom2_word = rp2040_rom2(cmd[10:5]);
    wire [31:0] rp2040_rom2_nibble = rp2040_rom2_word >> {cmd[4:3], ~cmd[2], 2'b00};

    wire [7:0] ram_data = data[cmd[RAM_LEN_BITS-1+3:3]];

    always @(negedge spi_clk) begin
        if (cmd[11]) begin
            q_data_out <= cmd[2] ? ram_data[3:0] : ram_data[7:4];
        end else if (cmd[12]) begin
            q_data_out <= rp2040_rom2_nibble[3:0];
        end else begin
            q_data_out <= rp2040_rom_nibble[3:0];
        end
        data_out_bits <= 2'h3 - cmd[1:0];
    end
    assign data_out = q_data_out[data_out_bits];
    assign spi_miso = reading ? data_out : 0;
    assign spi_d_out = quad ? q_data_out : {2'b0, spi_miso, 1'b0};

    wire [5:0] next_start_count = {1'b0,start_count} + 6'd1;
    wire [31:0] next_cmd = {cmd[30:0],spi_mosi};

    always @(posedge spi_clk or posedge spi_select) begin
        if (spi_select) begin
            start_count <= 0;
            cmd <= 0;
            reading <= 0;
            writing <= 0;
            bad_cmd <= 0;
            spi_d_oe <= 4'b0000;
            quad <= 0;
            delay <= 0;
        end else begin
            start_count <= next_start_count[4:0];

            if (!reading && !writing && !bad_cmd) begin
                cmd <= next_cmd[30:0];
                if (next_start_count == 31) begin
                    if (next_cmd[30:23] == 8'h03) begin
                        spi_d_oe <= 4'b0010;
                    end
                end
                if (next_start_count == 32) begin
                    cmd <= {next_cmd[27:0], 3'h0};
                    if (next_cmd[31:24] == 3) begin
                        reading <= 1;
                        quad <= 0;
                    end else if (next_cmd[31:24] == 2) begin
                        writing <= 1;
                        quad <= 0;
                    end else if (next_cmd[31:24] == 8'h6B) begin
                        reading <= 1;
                        quad <= 1;
                        delay <= 1;
                    end else if (next_cmd[31:24] == 8'h32) begin
                        writing <= 1;
                        quad <= 1;
                    end else begin
                        bad_cmd <= 1;
                        quad <= 0;
                    end
                end
            end else if (delay) begin
                if (next_start_count == FAST_READ_DELAY - 1) begin
                    spi_d_oe <= 4'b1111;
                end
                if (next_start_count == FAST_READ_DELAY) begin
                    delay <= 0;
                end
            end else if (reading || writing) begin
                cmd <= cmd + (quad ? 4 : 1);
            end
        end
    end

    always @(posedge debug_clk) begin
        byte_out <= data[addr_in];
    end

    // This ROM at memory address 0 launches the RP2040 into XIP mode (QSPI)
    // And starts execution at 0x10000200 (address 0x200 in flash)
    function [31:0] rp2040_rom(input [5:0] addr);
        case(addr)
0: rp2040_rom = 32'h4a284b27;
1: rp2040_rom = 32'h2105601a;
2: rp2040_rom = 32'h64b94f27;
3: rp2040_rom = 32'h65b96539;
4: rp2040_rom = 32'h204a4d26;
5: rp2040_rom = 32'h66686628;
6: rp2040_rom = 32'h064a06be;
7: rp2040_rom = 32'h21006232;
8: rp2040_rom = 32'h03806cf8;
9: rp2040_rom = 32'h61f2d505;
10: rp2040_rom = 32'h3c010b74;
11: rp2040_rom = 32'h3101d1fd;
12: rp2040_rom = 32'h2318e7f6;
13: rp2040_rom = 32'h2200061b;
14: rp2040_rom = 32'h221f609a;
15: rp2040_rom = 32'h601a0412;
16: rp2040_rom = 32'h609a2201;
17: rp2040_rom = 32'h661d4d1a;
18: rp2040_rom = 32'h6c786619;
19: rp2040_rom = 32'hd5030380;
20: rp2040_rom = 32'h010921ab;
21: rp2040_rom = 32'he0126619;
22: rp2040_rom = 32'h2a0e6a9a;
23: rp2040_rom = 32'h6e1ad1fc;
24: rp2040_rom = 32'h4a146e19;
25: rp2040_rom = 32'h6619661a;
26: rp2040_rom = 32'h2a0e6a9a;
27: rp2040_rom = 32'h6e1ad1fc;
28: rp2040_rom = 32'h4c116e19;
29: rp2040_rom = 32'h39016121;
30: rp2040_rom = 32'h661a1d2a;
31: rp2040_rom = 32'h6a9a6619;
32: rp2040_rom = 32'hd1fc2a0e;
33: rp2040_rom = 32'h609a2200;
34: rp2040_rom = 32'h6019490c;
35: rp2040_rom = 32'h33f4490c;
36: rp2040_rom = 32'h3bf46019;
37: rp2040_rom = 32'h2101605a;
38: rp2040_rom = 32'h490a6099;
39: rp2040_rom = 32'h00004708;
40: rp2040_rom = 32'h4000f000;
41: rp2040_rom = 32'h00804020;
42: rp2040_rom = 32'h40014074;
43: rp2040_rom = 32'h4001c000;
44: rp2040_rom = 32'h02000100;
45: rp2040_rom = 32'h03000104;
46: rp2040_rom = 32'h40060000;
47: rp2040_rom = 32'h005f0300;
48: rp2040_rom = 32'h6b001218;
49: rp2040_rom = 32'h10000201;
            63: rp2040_rom = 32'ha5d88739;
            default:    
                rp2040_rom = 0;
        endcase
    endfunction

    function [31:0] rp2040_rom2(input [5:0] addr);
        case(addr)
0: rp2040_rom2 = 32'h4a0c4b0b;
1: rp2040_rom2 = 32'h2104601a;
2: rp2040_rom2 = 32'h200562d1;
3: rp2040_rom2 = 32'h4d0a6250;
4: rp2040_rom2 = 32'h6668204a;
5: rp2040_rom2 = 32'h20014b09;
6: rp2040_rom2 = 32'h03416018;
7: rp2040_rom2 = 32'h28011840;
8: rp2040_rom2 = 32'h4249d101;
9: rp2040_rom2 = 32'h60d81840;
10: rp2040_rom2 = 32'h03a46a14;
11: rp2040_rom2 = 32'he7f2d4f6;
12: rp2040_rom2 = 32'h4000f000;
13: rp2040_rom2 = 32'h400140a0;
14: rp2040_rom2 = 32'h4001c000;
15: rp2040_rom2 = 32'h40050050;
            default:    
                rp2040_rom2 = 0;
        endcase
    endfunction
endmodule
