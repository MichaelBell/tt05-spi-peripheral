`default_nettype none
`timescale 1ns/1ps

/*
this testbench just instantiates the module and makes some convenient wires
that can be driven / tested by the cocotb test.py
*/

// testbench is controlled by test.py
module tb ();

    // this part dumps the trace to a vcd file that can be viewed with GTKWave
    initial begin
        $dumpfile ("tb.vcd");
        $dumpvars (0, tb);
        #1;
    end

    // wire up the inputs and outputs
    reg  clk;
    reg  rst_n;
    reg  ena;

    reg  debug_clk;
    reg  spi_select;
    reg  [3:0] debug_addr;
    reg  [7:6] ui_in;

    reg  spi_mosi;
    reg  [7:1] uio_in;

    wire [6:0] segments = uo_out[6:0];
    wire dot = uo_out[7];
    wire [7:0] uo_out;
    
    wire spi_miso = uio_out[1];
    wire [3:0] spi_q_data_out = uio_out[3:0];
    wire [3:0] debug_data = uio_out[7:4];
    wire [7:0] uio_out;

    wire [7:0] uio_oe;

    tt_um_MichaelBell_spi_peri i_tt (
    // include power ports for the Gate Level test
    `ifdef GL_TEST
        .VPWR( 1'b1),
        .VGND( 1'b0),
    `endif
        .ui_in      ({ui_in, debug_addr, spi_select, clk}),    // Dedicated inputs
        .uo_out     (uo_out),   // Dedicated outputs
        .uio_in     ({uio_in, spi_mosi}),   // IOs: Input path
        .uio_out    (uio_out),  // IOs: Output path
        .uio_oe     (uio_oe),   // IOs: Enable path (active high: 0=input, 1=output)
        .ena        (ena),      // enable - goes high when design is selected
        .clk        (debug_clk),      // clock
        .rst_n      (rst_n)     // not reset
        );

endmodule
