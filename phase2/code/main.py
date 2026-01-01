import os
import argparse

MemSize = 1000 # memory size, in reality, the memory size should be 2^32, but for this lab, for the space resaon, we keep it as this large number, but the memory is still 32-bit addressable.

class InsMem(object):
    def __init__(self, name, ioDir):
        self.id = name
        
        with open(os.path.join(ioDir, "imem.txt")) as im:
            self.IMem = [data.replace("\n", "") for data in im.readlines()]

    def readInstr(self, ReadAddress):
        #read instruction memory
        #return 32 bit hex val showing the instruction

        # Start from read adress (check no out of range memory access)
        if ReadAddress >= len(self.IMem):
            return "0" * 8  # Return 0 if out of bounds
        
        # Concatenate 4 consecutive bytes - big endian
        instruct = ""
        for i in range(4):
            if ReadAddress + i > len(self.IMem):
                instruct += "00000000" # Additional zeros if instruction reaches end
            else:
                instruct += self.IMem[ReadAddress + i]
        
        return instruct
          
class DataMem(object):
    def __init__(self, name, ioDir):
        self.id = name
        self.ioDir = ioDir
        with open(os.path.join(ioDir, "dmem.txt")) as dm:
            self.DMem = [data.replace("\n", "") for data in dm.readlines()]

    def readInstr(self, ReadAddress):
        #read data memory
        #return 32 bit hex val
        
        # Start from read adress (check no out of range memory access)
        if ReadAddress >= len(self.DMem):
            return "0" * 8
        
        data = ""
        
        # Concatenate 4 consecutive bytes - big endian
        for i in range(4):
            if ReadAddress + i < len(self.DMem):
                data += self.DMem[ReadAddress + i]
            else:
                data += "00000000" # If address exceeds bounds, add zeros
        
        return data
        
    def writeDataMem(self, Address, WriteData):
        # write data into byte addressable memory
        if Address >= len(self.DMem):
            return
        
        # WriteData to 32-bit string conversion
        if isinstance(WriteData, int):
            if WriteData < 0:
                # unsigned transformation
                WriteData = (1 << 32) + WriteData  
            data_in_binary = format(WriteData, '032b')
        else:
            # Write Data already a binary string
            data_in_binary = format(int(WriteData, 2) if len(WriteData) <= 32 else int(WriteData[:32], 2), '032b')
        
        # Write 4 bytes 
        for i in range(4):
            if Address + i < len(self.DMem):
                self.DMem[Address + i] = data_in_binary[i*8:(i+1)*8] # write 1 byte at a time
                     
    def outputDataMem(self):
        resPath = os.path.join(self.ioDir, self.id + "_DMEMResult.txt")
        with open(resPath, "w") as rp:
            rp.writelines([str(data) + "\n" for data in self.DMem])
            # Add zeros if needed to match test cases
            extra_0 = MemSize - len(self.DMem)
            if extra_0 > 0:
                rp.writelines(["00000000\n"] * extra_0)

class RegisterFile(object):
    def __init__(self, ioDir, prefix=""):
        self.outputFile = os.path.join(ioDir, prefix + "RFResult.txt")
        self.Registers = [0x0 for i in range(32)]
    
    def readRF(self, Reg_addr):
        return self.Registers[Reg_addr] # return 32-bit integer val stored in register address
    
    def writeRF(self, Reg_addr, Wrt_reg_data):
        if Reg_addr != 0:
            self.Registers[Reg_addr] = Wrt_reg_data
         
    def outputRF(self, cycle):
        op = ["-"*70+"\n", "State of RF after executing cycle: " + str(cycle) + "\n"]
        op.extend([format(val & 0xFFFFFFFF, '032b') + "\n" for val in self.Registers])
    
        if(cycle == 0):
            perm = "w"
        else:
            perm = "a"
        
        outdir = os.path.dirname(self.outputFile)
        if outdir and not os.path.exists(outdir):
            os.makedirs(outdir, exist_ok=True)
        with open(self.outputFile, perm) as file:
            file.writelines(op)

class State(object):
    def __init__(self):
        self.IF = {"nop": False, "PC": 0}
        self.ID = {"nop": False, "Instr": 0}
        self.EX = {"nop": False, "Read_data1": 0, "Read_data2": 0, "Imm": 0, "Rs": 0, "Rt": 0, "Wrt_reg_addr": 0, "is_I_type": False, "rd_mem": 0, 
                   "wrt_mem": 0, "alu_op": 0, "wrt_enable": 0}
        self.MEM = {"nop": False, "ALUresult": 0, "Store_data": 0, "Rs": 0, "Rt": 0, "Wrt_reg_addr": 0, "rd_mem": 0, 
                   "wrt_mem": 0, "wrt_enable": 0}
        self.WB = {"nop": False, "Wrt_data": 0, "Rs": 0, "Rt": 0, "Wrt_reg_addr": 0, "wrt_enable": 0}

class Core(object):
    def __init__(self, ioDir, imem, dmem, prefix=""):
        self.myRF = RegisterFile(ioDir, prefix)
        self.cycle = 0
        self.halted = False
        self.ioDir = ioDir
        self.prefix = prefix
        self.state = State()
        self.nextState = State()
        self.ext_imem = imem
        self.ext_dmem = dmem
        self.instruction_count = 0
        self.total_cycles = 0.      

class SingleStageCore(Core):
    def __init__(self, ioDir, imem, dmem):
        super(SingleStageCore, self).__init__(ioDir, imem, dmem, "SS_")
        self.opFilePath = os.path.join(ioDir, "StateResult_SS.txt")

    def step(self):

        # ==========================================================
        # (IF) Instruction Fetch
        # (ID) Instruction Decode
        # (EX) Execute / ALU Operation
        # (MEM) Memory Access
        # (WB) Write Back
        # ==========================================================


        # Halt check --> stop execution if NOP encountered
        if self.state.IF["nop"]:
            self.halted = True
            self.myRF.outputRF(self.cycle)
            self.printState(self.state, self.cycle)
            self.cycle += 1
            self.total_cycles = self.cycle
            return
        
        # Fetch instruction
        PC = self.state.IF["PC"]
        binary_instruction = self.ext_imem.readInstr(PC)
        
        # print(f"Cycle {self.cycle}: PC={PC}, Fetched: {instruction_binary[:16]}...")

        # check for invalid or halt instruction
        if binary_instruction == "1" * 32 or len(binary_instruction) < 32:
            # HALT instruction (it counts)
            self.instruction_count += 1
            # print(f"  -> Executing HALT instruction #{self.instruction_count}")
            
            # halt
            self.nextState.IF["nop"] = True
            
            # Check if next PC is valid 
            next_PC = PC + 4
            if next_PC < len(self.ext_imem.IMem):
                self.nextState.IF["PC"] = next_PC  # Advance if valid
            else:
                self.nextState.IF["PC"] = PC  # else, stay if not
            
            # Output state
            self.myRF.outputRF(self.cycle)
            self.printState(self.nextState, self.cycle)
            
            # Update state --> increment cycle
            self.state = self.nextState
            self.cycle += 1
            self.total_cycles = self.cycle
            return
        
        # instruction count (only count actual instructions, not HALT)
        self.instruction_count += 1

        # print(f"  -> Executing instruction #{self.instruction_count}")
        
        instr = int(binary_instruction, 2)
        opcode = instr & 0x7F
        rd = (instr >> 7) & 0x1F
        funct3 = (instr >> 12) & 0x7
        rs1 = (instr >> 15) & 0x1F
        rs2 = (instr >> 20) & 0x1F
        funct7 = (instr >> 25) & 0x7F

        # ----------------Execution stage - ALU Operations---------------------
        # =====================================================================
        # R - Type instructions
        # =====================================================================
        if opcode == 0x33:
            val_rs1 = self.myRF.readRF(rs1)
            val_rs2 = self.myRF.readRF(rs2)

            # ADD
            if funct3 == 0x0 and funct7 == 0x00:
                result = (val_rs1 + val_rs2) & 0xFFFFFFFF

            # SUB
            elif funct3 == 0x0 and funct7 == 0x20:    
                result = (val_rs1 - val_rs2) & 0xFFFFFFFF

            # XOR
            elif funct3 == 0x4:                   
                result = val_rs1 ^ val_rs2

            # OR
            elif funct3 == 0x6:                       
                result = val_rs1 | val_rs2

            # AND
            elif funct3 == 0x7:                 
                result = val_rs1 & val_rs2

            else:
                result = 0

            self.myRF.writeRF(rd, result)
            self.nextState.IF["PC"] = PC + 4

        # =====================================================================
        # I - Type Arithmetic instructions
        # =====================================================================
        elif opcode == 0x13:
            imm = (instr >> 20) & 0xFFF
            if imm & 0x800:  # Sign extend 12-bit
                imm |= 0xFFFFF000

            val_rs1 = self.myRF.readRF(rs1)

            # ADDI
            if funct3 == 0x0:
                result = (val_rs1 + imm) & 0xFFFFFFFF

            # XORI
            elif funct3 == 0x4:
                result = val_rs1 ^ imm

            # ORI
            elif funct3 == 0x6:
                result = val_rs1 | imm

            # ANDI
            elif funct3 == 0x7:
                result = val_rs1 & imm
            else:
                result = 0

            self.myRF.writeRF(rd, result)
            self.nextState.IF["PC"] = PC + 4

        # -------------- Memory Access Stage operations -----------------------
        # =====================================================================
        # LOAD
        # =====================================================================
        elif opcode == 0x03:
            imm = (instr >> 20) & 0xFFF
            if imm & 0x800:
                imm |= 0xFFFFF000
            addr = (self.myRF.readRF(rs1) + imm) & 0xFFFFFFFF
            data_binary = self.ext_dmem.readInstr(addr)
            data = int(data_binary, 2)
            self.myRF.writeRF(rd, data)
            self.nextState.IF["PC"] = PC + 4

        # =====================================================================
        # STORE
        # =====================================================================
        elif opcode == 0x23:
            imm = (((instr >> 25) & 0x7F) << 5) | ((instr >> 7) & 0x1F)
            if imm & 0x800:
                imm |= 0xFFFFF000
            addr = (self.myRF.readRF(rs1) + imm) & 0xFFFFFFFF
            data = self.myRF.readRF(rs2)
            self.ext_dmem.writeDataMem(addr, data)
            self.nextState.IF["PC"] = PC + 4

        # =====================================================================
        # BRANCH INSTRUCTION --> checks which branch condition and updates PC
        # =====================================================================
        elif opcode == 0x63:
            imm = (((instr >> 31) & 0x1) << 12) | \
                (((instr >> 7) & 0x1) << 11) | \
                (((instr >> 25) & 0x3F) << 5) | \
                (((instr >> 8) & 0xF) << 1)
            if imm & 0x1000:
                imm |= 0xFFFFE000

            val_rs1 = self.myRF.readRF(rs1)
            val_rs2 = self.myRF.readRF(rs2)
            
            # Helper function to convert to signed 32-bit
            def to_signed_32(val):
                if val & 0x80000000:
                    return val - 0x100000000
                return val
            
            chosen_branch = False

            # BEQ
            if funct3 == 0x0:      
                chosen_branch = (val_rs1 == val_rs2)

            # BNE
            elif funct3 == 0x1:  
                chosen_branch = (val_rs1 != val_rs2)

            # BLT (signed comparison)
            elif funct3 == 0x4:
                val_rs1_signed = to_signed_32(val_rs1)
                val_rs2_signed = to_signed_32(val_rs2)
                chosen_branch = (val_rs1_signed < val_rs2_signed)

            # BGE (signed comparison)
            elif funct3 == 0x5:
                val_rs1_signed = to_signed_32(val_rs1)
                val_rs2_signed = to_signed_32(val_rs2)
                chosen_branch = (val_rs1_signed >= val_rs2_signed)

            if chosen_branch:
                self.nextState.IF["PC"] = (PC + imm) & 0xFFFFFFFF
            else:
                self.nextState.IF["PC"] = PC + 4
        # ==========================================================
        # JAL INSTRUCTION
        # ==========================================================
        elif opcode == 0x6F:
            imm = (((instr >> 31) & 0x1) << 20) | \
                  (((instr >> 12) & 0xFF) << 12) | \
                  (((instr >> 20) & 0x1) << 11) | \
                  (((instr >> 21) & 0x3FF) << 1)
            if imm & 0x100000:
                imm |= 0xFFE00000
            self.myRF.writeRF(rd, PC + 4)
            self.nextState.IF["PC"] = (PC + imm) & 0xFFFFFFFF

        # Move PC by 4 to avoid stalling
        else:
            self.nextState.IF["PC"] = PC + 4

        # (WB) WRITE BACK STAGE (completed within cycle)
        self.myRF.outputRF(self.cycle)
        self.printState(self.nextState, self.cycle)

        # Move to next state --> Increase cycle counter 
        self.state = self.nextState
        self.cycle += 1
        self.total_cycles = self.cycle 

    def printState(self, state, cycle):
        printstate = ["-"*70+"\n", "State after executing cycle: " + str(cycle) + "\n"]
        printstate.append("IF.PC: " + str(state.IF["PC"]) + "\n")
        printstate.append("IF.nop: " + str(state.IF["nop"]) + "\n")
        
        if(cycle == 0): perm = "w"
        else: perm = "a"
        with open(self.opFilePath, perm) as wf:
            wf.writelines(printstate)


class FiveStageCore(Core):
    def __init__(self, ioDir, imem, dmem):
        super(FiveStageCore, self).__init__(ioDir, imem, dmem)
        self.opFilePath = os.path.join(ioDir, "StateResult_FS.txt")
        self.myRF = RegisterFile(ioDir, "FS_")
        self.all_nops_detected = False
        # Checks if HALT is fetched or not
        self.halt_fetched = False  
        
        # Initialize PCs for stages
        self.state.ID["PC"] = 0
        self.state.EX["PC"] = 0
        self.state.MEM["PC"] = 0
        self.state.WB["PC"] = 0
        self.nextState.ID["PC"] = 0
        self.nextState.EX["PC"] = 0
        self.nextState.MEM["PC"] = 0
        self.nextState.WB["PC"] = 0

    def step(self):
        # Halt check
        if self.halted:
            return
        
        # control flags
        stall_IF_ID = False
        stall_ID_EX = False
        flush_IF_ID = False
        br_taken = False
        br_target = 0
        jal_taken = False
        jal_target = 0
        

        # Implementing the stages in the opposite way because 
        # the lower states are affected by the upper states nops
        # --------------------- WB stage ---------------------
        if not self.state.WB["nop"]:
            is_real_instruction = (self.state.WB["wrt_enable"] == 1 or 
                                  self.state.WB.get("rd_mem", 0) == 1 or 
                                  self.state.WB.get("wrt_mem", 0) in [1, 2, 3])
            
            if is_real_instruction:
                self.instruction_count += 1
                # Debug statements I implemented to track stages
                # print(f"[CYCLE {self.cycle}] WB counting instruction: wrt_enable={self.state.WB['wrt_enable']}, rd_mem={self.state.WB.get('rd_mem', 0)}, wrt_mem={self.state.WB.get('wrt_mem', 0)}, reg={self.state.WB.get('Wrt_reg_addr', 0)}")

        if not self.state.WB["nop"] and self.state.WB["wrt_enable"] == 1:
            self.myRF.writeRF(self.state.WB["Wrt_reg_addr"], self.state.WB["Wrt_data"])
        
        # --------------------- MEM stage --------------------
        if not self.state.MEM["nop"]:
            alu_result = self.state.MEM["ALUresult"]
            
            # Memory access
            if self.state.MEM["rd_mem"] == 1:
                data_binary = self.ext_dmem.readInstr(alu_result)
                wrt_data = int(data_binary, 2)
            else:
                wrt_data = alu_result
            
            # Store
            if self.state.MEM["wrt_mem"] == 1:
                store_data = self.state.MEM["Store_data"]
                self.ext_dmem.writeDataMem(alu_result, store_data)
            
            # Pass to WB
            self.nextState.WB.update({
                "nop": False,
                "Wrt_data": wrt_data,
                "Rs": self.state.MEM["Rs"],
                "Rt": self.state.MEM["Rt"],
                "Wrt_reg_addr": self.state.MEM["Wrt_reg_addr"],
                "wrt_enable": self.state.MEM["wrt_enable"],
                "rd_mem": self.state.MEM["rd_mem"],
                "wrt_mem": self.state.MEM["wrt_mem"],
                "PC": self.state.MEM["PC"]
            })
        else:
            self.nextState.WB["nop"] = True
            self.nextState.WB["wrt_enable"] = 0
            self.nextState.WB["rd_mem"] = 0
            self.nextState.WB["wrt_mem"] = 0
        
        # --------------------- EX stage ---------------------
        if not self.state.EX["nop"]:
            # Get operands with forwarding
            operand1 = self.state.EX["Read_data1"]
            operand2 = self.state.EX["Read_data2"] if not self.state.EX["is_I_type"] else self.state.EX["Imm"]
            
            # Forwarding from MEM stage
            if (not self.state.MEM["nop"] and 
                self.state.MEM["wrt_enable"] == 1 and 
                self.state.MEM["Wrt_reg_addr"] != 0):
                
                if self.state.MEM["Wrt_reg_addr"] == self.state.EX["Rs"]:
                    if self.state.MEM["rd_mem"] == 0:
                        operand1 = self.state.MEM["ALUresult"]
                
                if (not self.state.EX["is_I_type"] and 
                    self.state.MEM["Wrt_reg_addr"] == self.state.EX["Rt"] and
                    self.state.MEM["rd_mem"] == 0):
                    operand2 = self.state.MEM["ALUresult"]
            
            # ALU operation
            alu_op = self.state.EX["alu_op"]
            result = 0
            
            if alu_op == 0:  # ADD
                result = (operand1 + operand2) & 0xFFFFFFFF
            elif alu_op == 1:  # SUB
                result = (operand1 - operand2) & 0xFFFFFFFF
            elif alu_op == 2:  # XOR
                result = (operand1 ^ operand2) & 0xFFFFFFFF
            elif alu_op == 3:  # OR
                result = (operand1 | operand2) & 0xFFFFFFFF
            elif alu_op == 4:  # AND
                result = (operand1 & operand2) & 0xFFFFFFFF
            else:
                result = operand1  # For JAL
            
            # Pass to MEM
            self.nextState.MEM.update({
                "nop": False,
                "ALUresult": result,
                "Store_data": self.state.EX["Read_data2"],
                "Rs": self.state.EX["Rs"],
                "Rt": self.state.EX["Rt"],
                "Wrt_reg_addr": self.state.EX["Wrt_reg_addr"],
                "rd_mem": self.state.EX["rd_mem"],
                "wrt_mem": self.state.EX["wrt_mem"],
                "wrt_enable": self.state.EX["wrt_enable"],
                "PC": self.state.EX["PC"]
            })
        else:
            self.nextState.MEM["nop"] = True
            self.nextState.MEM["rd_mem"] = 0
            self.nextState.MEM["wrt_mem"] = 0
            self.nextState.MEM["wrt_enable"] = 0
        
        # --------------------- ID stage ---------------------
        if not self.state.ID["nop"]:
            instr = self.state.ID["Instr"]
            
            # Decode
            opcode = instr & 0x7F
            rd = (instr >> 7) & 0x1F
            funct3 = (instr >> 12) & 0x7
            rs_1 = (instr >> 15) & 0x1F
            rs_2 = (instr >> 20) & 0x1F
            funct7 = (instr >> 25) & 0x7F
            
            # Read registers
            val_rs1 = self.myRF.readRF(rs_1)
            val_rs2 = self.myRF.readRF(rs_2)
            
            # DEFAULT: pass nop to EX
            self.nextState.EX["nop"] = True
            self.nextState.EX["wrt_enable"] = 0
            self.nextState.EX["rd_mem"] = 0
            self.nextState.EX["wrt_mem"] = 0
            self.nextState.EX["PC"] = self.state.ID["PC"]
            
            # Load-use hazard detection
            load_use_hazard = False
            if (not self.state.EX["nop"] and 
                self.state.EX["rd_mem"] == 1 and 
                self.state.EX["wrt_enable"] == 1):
                
                ex_dest = self.state.EX["Wrt_reg_addr"]
                
                if ex_dest != 0:
                    if opcode in [0x33, 0x13, 0x03, 0x23] and ex_dest == rs_1:
                        load_use_hazard = True
                    
                    if opcode in [0x33, 0x23] and ex_dest == rs_2:
                        load_use_hazard = True
                    
                    if opcode == 0x63:
                        if ex_dest == rs_1 or ex_dest == rs_2:
                            load_use_hazard = True
            
            # Handle load-use hazard stall
            if load_use_hazard:
                stall_IF_ID = True
                stall_ID_EX = True
                
                self.nextState.EX["nop"] = True
                self.nextState.EX["wrt_enable"] = 0
                self.nextState.EX["rd_mem"] = 0
                self.nextState.EX["wrt_mem"] = 0
                
                self.nextState.ID["nop"] = self.state.ID["nop"]
                self.nextState.ID["Instr"] = self.state.ID["Instr"]
                self.nextState.ID["PC"] = self.state.ID["PC"]
            else:
                # R-type
                if opcode == 0x33:
                    self.nextState.EX["nop"] = False
                    self.nextState.EX["Read_data1"] = val_rs1
                    self.nextState.EX["Read_data2"] = val_rs2
                    self.nextState.EX["Rs"] = rs_1
                    self.nextState.EX["Rt"] = rs_2
                    self.nextState.EX["Wrt_reg_addr"] = rd
                    self.nextState.EX["is_I_type"] = False
                    self.nextState.EX["wrt_enable"] = 1
                    
                    if funct3 == 0x0 and funct7 == 0x00:
                        self.nextState.EX["alu_op"] = 0
                    elif funct3 == 0x0 and funct7 == 0x20:
                        self.nextState.EX["alu_op"] = 1
                    elif funct3 == 0x4:
                        self.nextState.EX["alu_op"] = 2
                    elif funct3 == 0x6:
                        self.nextState.EX["alu_op"] = 3
                    elif funct3 == 0x7:
                        self.nextState.EX["alu_op"] = 4
                
                # I-type arithmetic
                elif opcode == 0x13:
                    imm = (instr >> 20) & 0xFFF
                    if imm & 0x800:
                        imm |= 0xFFFFF000
                    
                    self.nextState.EX["nop"] = False
                    self.nextState.EX["Read_data1"] = val_rs1
                    self.nextState.EX["Imm"] = imm
                    self.nextState.EX["Rs"] = rs_1
                    self.nextState.EX["Wrt_reg_addr"] = rd
                    self.nextState.EX["is_I_type"] = True
                    self.nextState.EX["wrt_enable"] = 1
                    
                    if funct3 == 0x0:
                        self.nextState.EX["alu_op"] = 0
                    elif funct3 == 0x4:
                        self.nextState.EX["alu_op"] = 2
                    elif funct3 == 0x6:
                        self.nextState.EX["alu_op"] = 3
                    elif funct3 == 0x7:
                        self.nextState.EX["alu_op"] = 4
                
                # load
                elif opcode == 0x03:
                    imm = (instr >> 20) & 0xFFF
                    if imm & 0x800:
                        imm |= 0xFFFFF000
                    
                    self.nextState.EX["nop"] = False
                    self.nextState.EX["Read_data1"] = val_rs1
                    self.nextState.EX["Imm"] = imm
                    self.nextState.EX["Rs"] = rs_1
                    self.nextState.EX["Wrt_reg_addr"] = rd
                    self.nextState.EX["is_I_type"] = True
                    self.nextState.EX["rd_mem"] = 1
                    self.nextState.EX["wrt_enable"] = 1
                    self.nextState.EX["alu_op"] = 0
                
                # store
                elif opcode == 0x23:
                    imm = (((instr >> 25) & 0x7F) << 5) | ((instr >> 7) & 0x1F)
                    if imm & 0x800:
                        imm |= 0xFFFFF000
                    
                    self.nextState.EX["nop"] = False
                    self.nextState.EX["Read_data1"] = val_rs1
                    self.nextState.EX["Read_data2"] = val_rs2
                    self.nextState.EX["Imm"] = imm
                    self.nextState.EX["Rs"] = rs_1
                    self.nextState.EX["Rt"] = rs_2
                    self.nextState.EX["is_I_type"] = True
                    self.nextState.EX["wrt_mem"] = 1
                    self.nextState.EX["alu_op"] = 0
                    self.nextState.EX["Wrt_reg_addr"] = 0
                    self.nextState.EX["wrt_enable"] = 0
                
                # branch instructions and jumps
                elif opcode == 0x63:
                    imm = (((instr >> 31) & 0x1) << 12) | \
                          (((instr >> 7) & 0x1) << 11) | \
                          (((instr >> 25) & 0x3F) << 5) | \
                          (((instr >> 8) & 0xF) << 1)
                    if imm & 0x1000:
                        imm |= 0xFFFFE000
                    
                    branch_pc = self.state.ID["PC"]
                    target_pc = (branch_pc + imm) & 0xFFFFFFFF
                    taken = False
                    if funct3 == 0x0:
                        taken = (val_rs1 == val_rs2)
                    elif funct3 == 0x1:
                        taken = (val_rs1 != val_rs2)
                    elif funct3 == 0x4:
                        rs1_signed = val_rs1 if val_rs1 < 0x80000000 else val_rs1 - 0x100000000
                        rs2_signed = val_rs2 if val_rs2 < 0x80000000 else val_rs2 - 0x100000000
                        taken = (rs1_signed < rs2_signed)
                    elif funct3 == 0x5:
                        rs1_signed = val_rs1 if val_rs1 < 0x80000000 else val_rs1 - 0x100000000
                        rs2_signed = val_rs2 if val_rs2 < 0x80000000 else val_rs2 - 0x100000000
                        taken = (rs1_signed >= rs2_signed)
                    
                    # debug statement
                    # print(f"[CYCLE {self.cycle}] ID: BEQ at PC={branch_pc}, rs1={rs1}({val_rs1}), rs2={rs2}({val_rs2}), taken={taken}, target={target_pc if taken else 'N/A'}")
                    
                    self.nextState.EX["nop"] = False
                    self.nextState.EX["wrt_enable"] = 0
                    self.nextState.EX["rd_mem"] = 0
                    self.nextState.EX["wrt_mem"] = 2
                    self.nextState.EX["alu_op"] = 0
                    self.nextState.EX["Read_data1"] = 0
                    self.nextState.EX["Read_data2"] = 0
                    self.nextState.EX["Imm"] = 0
                    self.nextState.EX["is_I_type"] = False
                    self.nextState.EX["Wrt_reg_addr"] = 0
                    
                    if taken:
                        br_taken = True
                        br_target = target_pc
                        flush_IF_ID = True
                
                # JAL instruction
                elif opcode == 0x6F:
                    imm = (((instr >> 31) & 0x1) << 20) | \
                          (((instr >> 12) & 0xFF) << 12) | \
                          (((instr >> 20) & 0x1) << 11) | \
                          (((instr >> 21) & 0x3FF) << 1)
                    if imm & 0x100000:
                        imm |= 0xFFE00000
                    
                    jal_pc = self.state.ID["PC"]
                    target_pc = (jal_pc + imm) & 0xFFFFFFFF
                    return_addr = jal_pc + 4
                    

                    # Debug statement left to show my process
                    # print(f"[CYCLE {self.cycle}] ID: JAL at PC={jal_pc}, target={target_pc}, return_addr={return_addr}")
                    
                    self.nextState.EX["nop"] = False
                    self.nextState.EX["wrt_enable"] = 1
                    self.nextState.EX["Wrt_reg_addr"] = rd
                    self.nextState.EX["Read_data1"] = return_addr
                    self.nextState.EX["Read_data2"] = 0
                    self.nextState.EX["Imm"] = 0
                    self.nextState.EX["is_I_type"] = True
                    self.nextState.EX["alu_op"] = 0
                    self.nextState.EX["rd_mem"] = 0
                    self.nextState.EX["wrt_mem"] = 0
                    self.nextState.EX["Rs"] = 0
                    self.nextState.EX["Rt"] = 0
                    
                    jal_taken = True
                    jal_target = target_pc
                    flush_IF_ID = True
                
                elif instr == 0xFFFFFFFF:
                    # HALT going through pipeline
                    self.nextState.EX["nop"] = False
                    self.nextState.EX["wrt_enable"] = 0
                    self.nextState.EX["rd_mem"] = 0
                    self.nextState.EX["wrt_mem"] = 3  # indicates if halt
                    self.nextState.EX["alu_op"] = 0
                    self.nextState.EX["Read_data1"] = 0
                    self.nextState.EX["Read_data2"] = 0
                    self.nextState.EX["Imm"] = 0
                    self.nextState.EX["is_I_type"] = False
                    self.nextState.EX["Wrt_reg_addr"] = 0
                    # halt marker
                    self.halt_fetched = True
        else:
            self.nextState.EX["nop"] = True
            self.nextState.EX["wrt_enable"] = 0
            self.nextState.EX["rd_mem"] = 0
            self.nextState.EX["wrt_mem"] = 0
        
        # --------------------- IF stage ---------------------
        if stall_IF_ID:
            self.nextState.ID["nop"] = self.state.ID["nop"]
            self.nextState.ID["Instr"] = self.state.ID["Instr"]
            self.nextState.ID["PC"] = self.state.ID["PC"]
            self.nextState.IF["PC"] = self.state.IF["PC"]
            self.nextState.IF["nop"] = self.state.IF["nop"]
        elif flush_IF_ID:
            self.nextState.ID["nop"] = True
            self.nextState.ID["Instr"] = 0
            self.nextState.ID["PC"] = 0
            
            if br_taken:
                self.nextState.IF["PC"] = br_target
            elif jal_taken:
                self.nextState.IF["PC"] = jal_target
            self.nextState.IF["nop"] = False
        elif not self.state.IF["nop"]:
            PC = self.state.IF["PC"]
            binary_instruction = self.ext_imem.readInstr(PC)
            
            if binary_instruction == "1" * 32 or len(binary_instruction) < 32:
                # HALT instruction
                instr = int(binary_instruction[:32], 2) if len(binary_instruction) >= 32 else 0xFFFFFFFF
                self.nextState.ID["Instr"] = instr
                self.nextState.ID["nop"] = False
                self.nextState.ID["PC"] = PC
                self.nextState.IF["nop"] = True  # stop after halt
                self.nextState.IF["PC"] = PC
            else:
                # Normal instruction
                instr = int(binary_instruction, 2)
                self.nextState.ID["Instr"] = instr
                self.nextState.ID["nop"] = False
                self.nextState.ID["PC"] = PC
                self.nextState.IF["PC"] = PC + 4
                self.nextState.IF["nop"] = False
        else:
            self.nextState.IF["nop"] = True
            self.nextState.IF["PC"] = self.state.IF["PC"]
            self.nextState.ID["nop"] = True
            self.nextState.ID["Instr"] = 0
            self.nextState.ID["PC"] = 0
        
        if stall_ID_EX and not stall_IF_ID:
            self.nextState.EX["nop"] = True
            self.nextState.EX["wrt_enable"] = 0
            self.nextState.EX["rd_mem"] = 0
            self.nextState.EX["wrt_mem"] = 0
        
        self.myRF.outputRF(self.cycle)
        self.printState(self.nextState, self.cycle)
        
        # Update state
        self.state = self.nextState
        self.nextState = State()
        
        # Initialize PC fields in nextState
        self.nextState.ID["PC"] = 0
        self.nextState.EX["PC"] = 0
        self.nextState.MEM["PC"] = 0
        self.nextState.WB["PC"] = 0
        self.cycle += 1 # Increment cycle
        self.total_cycles = self.cycle
        
        # halt condition is checked if it has been fetched and went through the write back stage
        if self.halt_fetched:
            # implemented it until all stages go thru the nops
            all_nop = (self.state.IF["nop"] and self.state.ID["nop"] and 
                             self.state.EX["nop"] and self.state.MEM["nop"] and 
                             self.state.WB["nop"])
            
            if all_nop:
                self.halted = True #pipeline empty
        else:
            # halt condition for no halt specified instruction
            all_nop = (self.state.IF["nop"] and self.state.ID["nop"] and 
                             self.state.EX["nop"] and self.state.MEM["nop"] and 
                             self.state.WB["nop"])
            
            if all_nop and not self.all_nops_detected:
                self.all_nops_detected = True
            elif all_nop and self.all_nops_detected:
                self.halted = True

    def printState(self, state, cycle):
        printstate = ["-"*70+"\n", "State after executing cycle: " + str(cycle) + "\n"]
        printstate.extend(["IF." + key + ": " + str(val) + "\n" for key, val in state.IF.items()])
        printstate.extend(["ID." + key + ": " + str(val) + "\n" for key, val in state.ID.items()])
        printstate.extend(["EX." + key + ": " + str(val) + "\n" for key, val in state.EX.items()])
        printstate.extend(["MEM." + key + ": " + str(val) + "\n" for key, val in state.MEM.items()])
        printstate.extend(["WB." + key + ": " + str(val) + "\n" for key, val in state.WB.items()])

        if(cycle == 0): perm = "w"
        else: perm = "a"
        with open(self.opFilePath, perm) as wf:
            wf.writelines(printstate)

if __name__ == "__main__":
     
    #parse arguments for input file location
    parser = argparse.ArgumentParser(description='RV32I processor')
    parser.add_argument('--iodir', default="", type=str, help='Directory containing the input files.')
    args = parser.parse_args()

    ioDir = os.path.abspath(args.iodir)
    print("IO Directory:", ioDir)

    imem = InsMem("Imem", ioDir)
    dmem_ss = DataMem("SS", ioDir)
    dmem_fs = DataMem("FS", ioDir)
    
    ssCore = SingleStageCore(ioDir, imem, dmem_ss)
    fsCore = FiveStageCore(ioDir, imem, dmem_fs)

    while(True):
        if not ssCore.halted:
            ssCore.step()
        
        if not fsCore.halted:
            fsCore.step()

        if ssCore.halted and fsCore.halted:
            break
    
    # dump SS and FS data mem.
    dmem_ss.outputDataMem()
    dmem_fs.outputDataMem()


    # C3) Measure and report average CPI, Total execution cycles, 
    # and Instructions per cycle for both these cores by adding 
    # performance monitors to your code. (Submit code and print 
    # results to console or a file.) (5 points)

    # Print performance metrics for Single Stage
    
    print("SINGLE-STAGE CORE PERFORMANCE METRICS")
    print("="*60)
    print(f"Total Execution Cycles: {ssCore.total_cycles}")
    print(f"Total Instructions Executed: {ssCore.instruction_count}")
    if ssCore.instruction_count > 0:
        cpi = ssCore.total_cycles / ssCore.instruction_count
        ipc = ssCore.instruction_count / ssCore.total_cycles
        print(f"Average CPI (Cycles Per Instruction): {cpi:.4f}")
        print(f"IPC (Instructions Per Cycle): {ipc:.4f}")
    print("="*60)
    
    # Save performance metrics to file
    perf_path = os.path.join(ioDir, "PerformanceMetrics_SS.txt")
    with open(perf_path, "w") as pf:
        
        pf.write("Performance of Single Stage:\n")
        pf.write(f"#Cycles -> {ssCore.total_cycles}\n")
        pf.write(f"#Instructions -> {ssCore.instruction_count}\n")
        if ssCore.instruction_count > 0:
            cpi = ssCore.total_cycles / ssCore.instruction_count
            ipc = ssCore.instruction_count / ssCore.total_cycles
            pf.write(f"CPI -> {cpi}\n")
            pf.write(f"IPC -> {ipc}\n")

            
    # Print performance metrics for Five Stage
    print("\nFIVE-STAGE CORE PERFORMANCE METRICS")
    print("="*60)
    print(f"Total Execution Cycles: {fsCore.total_cycles}")
    print(f"Total Instructions Executed: {fsCore.instruction_count}")
    if fsCore.instruction_count > 0:
        cpi = fsCore.total_cycles / fsCore.instruction_count
        ipc = fsCore.instruction_count / fsCore.total_cycles
        print(f"Average CPI (Cycles Per Instruction): {cpi:.4f}")
        print(f"IPC (Instructions Per Cycle): {ipc:.4f}")
    print("="*60)

    # Save Five-Stage performance metrics to file
    perf_path_fs = os.path.join(ioDir, "PerformanceMetrics_FS.txt")
    with open(perf_path_fs, "w") as pf:
        pf.write("Performance of Five Stage:\n")
        pf.write(f"#Cycles -> {fsCore.total_cycles}\n")
        pf.write(f"#Instructions -> {fsCore.instruction_count}\n")
        if fsCore.instruction_count > 0:
            cpi = fsCore.total_cycles / fsCore.instruction_count
            ipc = fsCore.instruction_count / fsCore.total_cycles
            pf.write(f"CPI -> {cpi}\n")
            pf.write(f"IPC -> {ipc}\n")
