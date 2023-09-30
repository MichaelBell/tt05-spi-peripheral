// Copyright (C) 2023 Michael Bell
// SPI RAM that accepts reads and writes using
// commands 03h and 02h.

module spi_slave #( parameter RAM_LEN_BITS = 3 ) (
    input spi_clk,
    input spi_mosi,
    input spi_select,
    output spi_miso,

    input clk,
    input [RAM_LEN_BITS-1:0] addr_in,
    output reg [7:0] byte_out
);

    reg [30:0] cmd;
    reg [4:0] start_count;
    reg reading;
    reg writing;
    reg bad_cmd;

    reg [7:0] data [0:2**RAM_LEN_BITS-1];
    reg data_out;

    always @(posedge spi_clk) begin
        if (writing) begin
            data[cmd[RAM_LEN_BITS-1+3:3]][7 - cmd[2:0]] <= spi_mosi;
        end
    end

    wire [31:0] rp2040_rom_word = rp2040_rom(cmd[10:5]);

    always @(negedge spi_clk) begin
        if (cmd[11]) begin
            data_out <= data[cmd[RAM_LEN_BITS-1+3:3]][7 - cmd[2:0]];
        end else begin
            data_out <= rp2040_rom_word[{cmd[4:3], 3'h7 - cmd[2:0]}];
        end
    end
    assign spi_miso = reading ? data_out : 0;

    wire [5:0] next_start_count = {1'b0,start_count} + 6'd1;
    wire [31:0] next_cmd = {cmd[30:0],spi_mosi};

    always @(posedge spi_clk or posedge spi_select) begin
        if (spi_select) begin
            start_count <= 0;
            cmd <= 0;
            reading <= 0;
            writing <= 0;
            bad_cmd <= 0;
        end else begin
            start_count <= next_start_count[4:0];

            if (!reading && !writing && !bad_cmd) begin
                cmd <= next_cmd[30:0];
                if (next_start_count == 32) begin
                    cmd <= {next_cmd[27:0], 3'h0};
                    if (next_cmd[31:24] == 3)
                        reading <= 1;
                    else if (next_cmd[31:24] == 2)
                        writing <= 1;
                    else
                        bad_cmd <= 1;
                end
            end else if (reading || writing) begin
                cmd <= cmd + 1;
            end
        end
    end

    always @(posedge clk) begin
        byte_out <= data[addr_in];
    end

    function [31:0] rp2040_rom(input [5:0] addr);
        case(addr)
            //                7654321
            0:  rp2040_rom = 32'h4a084b07;
            1:  rp2040_rom = 32'h2104601a;
            2:  rp2040_rom = 32'h4b0762d1;
            3:  rp2040_rom = 32'h60182001;
            4:  rp2040_rom = 32'h18400341;
            5:  rp2040_rom = 32'hd1012801;
            6:  rp2040_rom = 32'h18404249;
            7:  rp2040_rom = 32'he7f860d8;
            8:  rp2040_rom = 32'h4000f000;
            9:  rp2040_rom = 32'h400140a0;
            10: rp2040_rom = 32'h40050050;
            63: rp2040_rom = 32'h1646a25a;
            default:    
                rp2040_rom = 0;
        endcase
    endfunction
endmodule
