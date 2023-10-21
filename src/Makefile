# Makefile
# See https://docs.cocotb.org/en/stable/quickstart.html for more info

# defaults
SIM ?= icarus
TOPLEVEL_LANG ?= verilog

# normal simulation
ifneq ($(GATES),yes)

# this is the only part you should need to modify:
COMPILE_ARGS    += -DSIM
VERILOG_SOURCES += $(PWD)/tb.v $(PWD)/top.v $(PWD)/spi_slave.v $(PWD)/decoder.v $(PWD)/ring_oscillator.v

else

# gate level simulation requires some extra setup, you shouldn't need to touch this
COMPILE_ARGS    += -DGL_TEST
COMPILE_ARGS    += -DFUNCTIONAL
COMPILE_ARGS    += -DUSE_POWER_PINS
COMPILE_ARGS    += -DSIM
COMPILE_ARGS    += -DUNIT_DELAY=\#1
VERILOG_SOURCES += $(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/verilog/primitives.v
VERILOG_SOURCES += $(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/verilog/sky130_fd_sc_hd.v

# this gets copied in by the GDS action workflow
VERILOG_SOURCES += $(PWD)/tb.v gate_level_netlist_modified.v inv_with_delay.v
endif

# TOPLEVEL is the name of the toplevel module in your Verilog or VHDL file
TOPLEVEL = tb

# MODULE is the basename of the Python test file
MODULE = test

# include cocotb's make rules to take care of the simulator setup
include $(shell cocotb-config --makefiles)/Makefile.sim

gate_level_netlist_modified.v: gate_level_netlist.v
	sed '/sky130_fd_sc_hd__inv_[12] \\i_spi\.rosc\..*\.inv/s/sky130_fd_sc_hd__inv_[12]/inv_with_delay/' gate_level_netlist.v > gate_level_netlist_modified.v

clean::
	rm -f gate_level_netlist_modified.v