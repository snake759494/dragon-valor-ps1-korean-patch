import capstone,struct,sys
ram=open(sys.argv[1],'rb').read()
md=capstone.Cs(capstone.CS_ARCH_MIPS,capstone.CS_MODE_MIPS32+capstone.CS_MODE_LITTLE_ENDIAN)
a=int(sys.argv[2],16)&0x1fffff; n=int(sys.argv[3])
for i in md.disasm(ram[a:a+n*4],0x80000000+a): print(hex(i.address),i.mnemonic,i.op_str)
