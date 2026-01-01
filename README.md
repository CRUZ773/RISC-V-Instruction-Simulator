**Implementation**

code/main.cpp - Complete single-stage processor implementation

* InsMem class: Instruction memory with big-endian support
* DataMem class: Data memory with read/write operations
* RegisterFile class: 32-bit register file with R0 constraint
* SingleStageCore class: Main processor with all 5 stages
* Performance metrics tracking (# of cycles & instructions, CPI & IPC)
  
**IMPORTANT: main.cpp expects imem.txt and dmem.txt in binary format from a directory, 8 bits (1 byte) per line**
