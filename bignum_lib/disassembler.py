# Copyright lowRISC contributors.
# Licensed under the Apache License, Version 2.0, see LICENSE for details.
# SPDX-License-Identifier: Apache-2.0

from . instructions import *


class Disassembler:
    ctx = InsContext()
    ins_objects = []
    loopendstack = []
    asm_lines = []

    def __init__(self, lines, label_lines=None, opt_print_bitmaps=False):
        self.ins_fac = InstructionFactory()
        self.lines = lines
        if label_lines:
            self.__parse_labels(label_lines)
        self.__dis_file(lines, opt_print_bitmaps)

    def __parse_labels(self, lines):
        label = ''
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.lower().startswith('@'):
                if line.lower().startswith('@0x'):
                    addr = int(line.split(':')[0][3:].strip(), 16)
                else:
                    addr = int(line.split(':')[0][1:].strip())
                fun_label = line.split('function')[1].split('{')[0].split('[')[0].strip()
                self.ctx.functions.update({addr: fun_label})
            if line.lower().startswith("0x") or line.split()[0].split(':')[0].isdigit():
                if label:
                    if line.lower().startswith("0x"):
                        addr = int(line.split()[0].split(':')[0][2:0], 16)
                    else:
                        addr = int(line.split()[0].split(':')[0])
                    self.ctx.labels.update({addr: label})
                    label = False
            if line.endswith(':'):
                label = line[:-1]

    def __dis_instr(self, ins_str):
        try:
            ins_object = self.ins_fac.factory_bin(ins_str[2:10], self.ctx)
            hexstr, asm_str, malformed = ins_object.get_asm_str()

        except UnknownOpcodeError:
            asm_str = 'Unknown Opcode'
            malformed = True
            hexstr = 'INVALID'
            ins_object = None
        return hexstr, asm_str, malformed, ins_object

    def __dis_file(self, lines, opt_print_bitmaps=False):
        if 0 not in self.ctx.functions:
            self.ctx.functions.update({0: 'fun0'})
        any_malformed = False
        for line in lines:
            if not line:
                break
            line = line.strip().lower()
            if len(line.split(':', 1)) == 2:
                line = line.split(':')[1].strip()
            if line.startswith("0x"):
                hexstr, asm_str, malformed, ins_object = self.__dis_instr(line)
                if opt_print_bitmaps:
                    print(ins_object.get_enc_tab())
                self.ins_objects.append((hexstr, asm_str, malformed, ins_object))
                if malformed:
                    any_malformed = True
                    print('malformed instruction word: ' + hexstr)
        if any_malformed:
            print('Warning: There were malformed instructions')
        else:
            print('No malformed instructions detected')

    def create_assembly(self, opt_address=False, opt_address_format=None, opt_function_length=False,
                        opt_code=False, opt_defines=False):
        """create assembly from instruction objects"""
        for i, item in enumerate(self.ins_objects):
            if isinstance(item[3], ILoop):
                self.loopendstack.append(item[3].get_len() + i)

            if i in self.ctx.functions:
                fun_len = 0
                for j in range(i+1, len(self.ins_objects) + 1):
                    fun_len = j-i
                    if j in self.ctx.functions:
                        break
                func = ''
                if i != 0:
                    if opt_code:
                        func += '/* } */\n'
                    else:
                        func += '}\n\n'
                if opt_code:
                    func += '/* '
                if opt_code or (opt_address and opt_address_format == 'hex'):
                    func += '@' + hex(i) + ': '
                if opt_address and opt_address_format == 'dec':
                    func += '@' + str(i) + ': '
                func += 'function ' + self.ctx.functions.get(i)
                if opt_function_length:
                    if fun_len:
                        func += '[' + str(fun_len) + ']'
                func += ' {'
                if opt_code:
                    func += ' */'
                self.asm_lines.append(func)
                if opt_code and opt_defines:
                    self.asm_lines.append('#define CF_' + self.ctx.functions.get(i) + '_adr ' + str(i))
            if i in self.ctx.labels:
                lab = ''
                if opt_code:
                    lab += '   /*'
                lab += self.ctx.labels.get(i) + ':'
                if opt_code:
                    lab += ' */'
                self.asm_lines.append(lab)
            asm = ''
            if opt_address:
                if opt_address_format == 'hex':
                    asm += '0x' + hex(i)[2:].zfill(3) + ': '
                else:
                    asm += str(i).zfill(4) + ':  '
            if opt_code:
                asm += '    ' + item[0] + ', /* '
            asm += item[1]
            if opt_code:
                asm += ' */'
            self.asm_lines.append(asm)
            if i in self.loopendstack:
                if opt_code:
                    self.asm_lines.append('	/*		   ) */')
                else:
                    if opt_address:
                        self.asm_lines.append('       )')
                    else:
                        self.asm_lines.append(')')
            if i == len(self.ins_objects) - 1:
                if opt_code:
                    self.asm_lines.append('/* } */')
                else:
                    self.asm_lines.append('}')
        return self.asm_lines

    def get_instruction_objects(self):
        return [item[3] for item in self.ins_objects]
