`default_nettype none

module tt_um_MichaelBell_spi_slave (
    input  wire [7:0] ui_in,    // Dedicated inputs - connected to the input switches
    output wire [7:0] uo_out,   // Dedicated outputs - connected to the 7 segment display
    input  wire [7:0] uio_in,   // IOs: Bidirectional Input path
    output wire [7:0] uio_out,  // IOs: Bidirectional Output path
    output wire [7:0] uio_oe,   // IOs: Bidirectional Enable path (active high: 0=input, 1=output)
    input  wire       ena,      // will go high when the design is enabled
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);

    wire [6:0] led_out;
    assign uo_out[6:0] = led_out;
    assign uo_out[7] = ui_in[1];  // SPI select debug

    // set bidirectionals
    assign uio_oe = 8'b11110010;

    // Tie unused outputs
    assign uio_out[0] = 1'b0;
    assign uio_out[3:2] = 2'd0;

    wire [7:0] debug_byte;
    wire [3:0] debug_nibble;

    // SPI slave
    spi_slave i_spi(
            .spi_clk(clk), 
            .spi_mosi(uio_in[0]), 
            .spi_select(ui_in[1] && rst_n), 
            .spi_miso(uio_out[1]), 
            .clk(ui_in[0]), 
            .addr_in(ui_in[5:3]), 
            .byte_out(debug_byte));

    assign debug_nibble = ui_in[2] ? debug_byte[7:4] : debug_byte[3:0];
    assign uio_out[7:4] = debug_nibble;

    // instantiate segment display
    seg7 seg7(.value(debug_nibble), .seg_out(led_out));

endmodule
