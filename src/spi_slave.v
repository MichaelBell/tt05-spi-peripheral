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
    output reg [7:0] byte_out,

    input rosc_ena
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

    wire [3:0] rosc_out;
    RingOscillator #(.NUM_FAST_CLKS(4), .STAGES(11)) rosc (
        .reset_n(rosc_ena),
        .fast_clk(rosc_out)
    );

    reg [3:0] buffered_rosc_out;
    always @(posedge spi_clk) begin
        buffered_rosc_out <= rosc_out;
    end

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
        end else if (cmd[13]) begin
            q_data_out <= buffered_rosc_out;
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
0: rp2040_rom = 32'h22014b29;
1: rp2040_rom = 32'h649a02d2;
2: rp2040_rom = 32'h4a294b28;
3: rp2040_rom = 32'h2105601a;
4: rp2040_rom = 32'h64b94f28;
5: rp2040_rom = 32'h65b96539;
6: rp2040_rom = 32'h204a4d27;
7: rp2040_rom = 32'h66686628;
8: rp2040_rom = 32'h064a06be;
9: rp2040_rom = 32'h21006232;
10: rp2040_rom = 32'h03806cf8;
11: rp2040_rom = 32'h61f2d505;
12: rp2040_rom = 32'h3c010b74;
13: rp2040_rom = 32'h3101d1fd;
14: rp2040_rom = 32'h2318e7f6;
15: rp2040_rom = 32'h2200061b;
16: rp2040_rom = 32'h221f609a;
17: rp2040_rom = 32'h601a0412;
18: rp2040_rom = 32'h609a2201;
19: rp2040_rom = 32'h661d4d1b;
20: rp2040_rom = 32'h6c786619;
21: rp2040_rom = 32'hd5030380;
22: rp2040_rom = 32'h010921ab;
23: rp2040_rom = 32'he0126619;
24: rp2040_rom = 32'h2a0e6a9a;
25: rp2040_rom = 32'h6e1ad1fc;
26: rp2040_rom = 32'h4a156e19;
27: rp2040_rom = 32'h6619661a;
28: rp2040_rom = 32'h2a0e6a9a;
29: rp2040_rom = 32'h6e1ad1fc;
30: rp2040_rom = 32'h4c126e19;
31: rp2040_rom = 32'h39016121;
32: rp2040_rom = 32'h661a1d2a;
33: rp2040_rom = 32'h6a9a6619;
34: rp2040_rom = 32'hd1fc2a0e;
35: rp2040_rom = 32'h609a2200;
36: rp2040_rom = 32'h6019490d;
37: rp2040_rom = 32'h33f4490d;
38: rp2040_rom = 32'h3bf46019;
39: rp2040_rom = 32'h2101605a;
40: rp2040_rom = 32'h490b6099;
41: rp2040_rom = 32'h00004708;
42: rp2040_rom = 32'h40008000;
43: rp2040_rom = 32'h4000f000;
44: rp2040_rom = 32'h00804020;
45: rp2040_rom = 32'h40014074;
46: rp2040_rom = 32'h4001c000;
47: rp2040_rom = 32'h02000100;
48: rp2040_rom = 32'h03000104;
49: rp2040_rom = 32'h40060000;
50: rp2040_rom = 32'h005f0300;
51: rp2040_rom = 32'h6b001218;
52: rp2040_rom = 32'h10000201;
            63: rp2040_rom = 32'hd3536af3;
            default:    
                rp2040_rom = 0;
        endcase
    endfunction

    function [31:0] rp2040_rom2(input [5:0] addr);
        case(addr)
0: rp2040_rom2 = 32'h21264a15;
1: rp2040_rom2 = 32'h21706251;
2: rp2040_rom2 = 32'h491462d1;
3: rp2040_rom2 = 32'h21026311;
4: rp2040_rom2 = 32'h4d136339;
5: rp2040_rom2 = 32'h26556829;
6: rp2040_rom2 = 32'h60116016;
7: rp2040_rom2 = 32'h21044d11;
8: rp2040_rom2 = 32'h4b1165b9;
9: rp2040_rom2 = 32'h60182001;
10: rp2040_rom2 = 32'h44080341;
11: rp2040_rom2 = 32'hd1012801;
12: rp2040_rom2 = 32'h44084249;
13: rp2040_rom2 = 32'h6cfc60d8;
14: rp2040_rom2 = 32'hd4f603a4;
15: rp2040_rom2 = 32'h60296829;
16: rp2040_rom2 = 32'h60116016;
17: rp2040_rom2 = 32'h60110a09;
18: rp2040_rom2 = 32'h140907c9;
19: rp2040_rom2 = 32'h6cfc60d9;
20: rp2040_rom2 = 32'hd5fc03a4;
21: rp2040_rom2 = 32'h0000e7e6;
22: rp2040_rom2 = 32'h40038000;
23: rp2040_rom2 = 32'h00000101;
24: rp2040_rom2 = 32'h10000100;
25: rp2040_rom2 = 32'h10000400;
26: rp2040_rom2 = 32'h40050050;
            default:    
                rp2040_rom2 = 0;
        endcase
    endfunction
endmodule
