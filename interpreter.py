import os
import re
import shutil
import subprocess

GCC="gcc"
LD="ld"
QEMU="qemu-system-i386"
ISO_DIR="iso"

generated_functions=""
generated_main=""
variables={}
block_stack=[]

KERNEL_TEMPLATE_START=r"""
#include <stdint.h>

__attribute__((section(".multiboot"), used))
const uint32_t multiboot_header[]={
0x1BADB002,0x0,0xE4524FFE
};

typedef unsigned short u16;
u16* video=(u16*)0xB8000;

int cursor=0;
const int WIDTH=80;
const int HEIGHT=25;

void scroll(){
    for(int y=1;y<HEIGHT;y++){
        for(int x=0;x<WIDTH;x++){
            video[(y-1)*WIDTH+x]=video[y*WIDTH+x];
        }
    }
    for(int x=0;x<WIDTH;x++){
        video[(HEIGHT-1)*WIDTH+x]=(0x0F<<8)|' ';
    }
    cursor=(HEIGHT-1)*WIDTH;
}

void putc(char c){
    if(c=='\n'){
        cursor=(cursor/WIDTH+1)*WIDTH;
    }else{
        video[cursor++]=(0x0F<<8)|c;
    }
    if(cursor>=WIDTH*HEIGHT) scroll();
}

void kprint(const char* s){
    int i=0;
    while(s[i]) putc(s[i++]);
}

void kprint_int(int v){
    char buf[12];
    int i=0,neg=0;
    if(v==0){ kprint("0"); return; }
    if(v<0){ neg=1; v=-v; }
    while(v){ buf[i++]='0'+v%10; v/=10; }
    if(neg) buf[i++]='-';
    buf[i]=0;
    for(int j=0;j<i/2;j++){
        char t=buf[j];
        buf[j]=buf[i-1-j];
        buf[i-1-j]=t;
    }
    kprint(buf);
}

int strcmp(const char* a,const char* b){
    while(*a && (*a==*b)){a++;b++;}
    return (unsigned char)*a-(unsigned char)*b;
}

static inline uint8_t inb(uint16_t p){
    uint8_t r;
    __asm__ volatile("inb %1,%0":"=a"(r):"Nd"(p));
    return r;
}

static inline uint8_t kb_read(){
    while(!(inb(0x64)&1)){}
    return inb(0x60);
}

char scancode_to_ascii(uint8_t sc){
    switch(sc){
        case 0x02:return '1';
        case 0x03:return '2';
        case 0x04:return '3';
        case 0x05:return '4';
        case 0x06:return '5';
        case 0x07:return '6';
        case 0x08:return '7';
        case 0x09:return '8';
        case 0x0A:return '9';
        case 0x0B:return '0';
        case 0x1E:return 'a';
        case 0x30:return 'b';
        case 0x2E:return 'c';
        case 0x20:return 'd';
        case 0x12:return 'e';
        case 0x21:return 'f';
        case 0x22:return 'g';
        case 0x23:return 'h';
        case 0x17:return 'i';
        case 0x24:return 'j';
        case 0x25:return 'k';
        case 0x26:return 'l';
        case 0x32:return 'm';
        case 0x31:return 'n';
        case 0x18:return 'o';
        case 0x19:return 'p';
        case 0x10:return 'q';
        case 0x13:return 'r';
        case 0x1F:return 's';
        case 0x14:return 't';
        case 0x16:return 'u';
        case 0x2F:return 'v';
        case 0x11:return 'w';
        case 0x2D:return 'x';
        case 0x15:return 'y';
        case 0x2C:return 'z';
        case 0x39:return ' ';
        case 0x1C:return '\n';
        case 0x0E:return '\b';
        default:return 0;
    }
}

char getch(){
    while(1){
        uint8_t sc=kb_read();
        if(sc&0x80) continue;
        char c=scancode_to_ascii(sc);
        if(c) return c;
    }
}

void read_line(char* buf,int max){
    int i=0;
    while(i<max-1){
        char c=getch();
        if(c=='\n'){ buf[i]=0; putc('\n'); return; }
        if(c=='\b'){
            if(i>0){
                i--;
                cursor--;
                video[cursor]=(0x0F<<8)|' ';
            }
            continue;
        }
        buf[i++]=c;
        putc(c);
    }
    buf[i]=0;
}

int read_int(){
    char buf[32];
    read_line(buf,32);
    int v=0,i=0;
    while(buf[i]){ v=v*10+(buf[i++]-'0'); }
    return v;
}

/* GENERATED FUNCTIONS */
"""

KERNEL_TEMPLATE_MIDDLE=r"""
void _start(){
/* GENERATED MAIN */
"""

KERNEL_TEMPLATE_END=r"""
while(1){__asm__("hlt");}
}
"""

def emit(l): 
    global generated_main
    generated_main+=l+"\n"

def translate_condition(tokens):
    if len(tokens)==3 and tokens[1] in ("==","!="):
        l,op,r=tokens
        if l in variables and variables[l]=="string":
            cmp=f"strcmp({l},{r})"
            return f"{cmp}==0" if op=="==" else f"{cmp}!=0"
    return " ".join(tokens)

def cmd_if(a):
    cond=translate_condition(a)
    emit(f"if({cond}){{")
    block_stack.append("if")

def cmd_else(a):
    emit("}else{")

def cmd_while(a):
    cond=translate_condition(a)
    emit(f"while({cond}){{")
    block_stack.append("while")

def cmd_end(a):
    if block_stack: block_stack.pop()
    emit("}")

def cmd_var(a):
    global generated_main
    t=a[0]
    name=a[1]

    if name in variables:
        return  # evita redeclaração

    variables[name]=t

    if t=="int":
        if len(a)>3 and a[2]=="=":
            generated_main = f"int {name}={a[3]};\n" + generated_main
        else:
            generated_main = f"int {name};\n" + generated_main

    if t=="string":
        generated_main = f"char {name}[256];\n" + generated_main

def cmd_set(a):
    emit(f"{a[0]}={' '.join(a[1:])};")

def cmd_print(a):
    for x in a:
        if x in variables:
            if variables[x]=="int":
                emit(f"kprint_int({x});")
            else:
                emit(f"kprint({x});")
        else:
            emit(f'kprint({x});')
    emit("putc('\\n');")

def cmd_input(a):
        name=a[0]
        if variables[name]=="int":
            emit(f"{name}=read_int();")
        else:
            emit(f"read_line({name}, sizeof({name}));")
COMMANDS={
"if":cmd_if,
"else":cmd_else,
"while":cmd_while,
"end":cmd_end,
"var":cmd_var,
"set":cmd_set,
"print":cmd_print,
"input":cmd_input
}

def split_tokens(l):
    return re.findall(r'"[^"]*"|\S+',l)

def interpretar():
    for f in os.listdir("."):
        if f.endswith(".kci"):
            for line in open(f):
                line=line.strip()
                if not line:continue
                parts=split_tokens(line)
                cmd=parts[0]
                if cmd in COMMANDS:
                    COMMANDS[cmd](parts[1:])

def build():
    with open("kernel.c","w") as f:
        f.write(KERNEL_TEMPLATE_START)
        f.write(generated_functions)
        f.write(KERNEL_TEMPLATE_MIDDLE)
        f.write(generated_main)
        f.write(KERNEL_TEMPLATE_END)

    subprocess.run([GCC,"-m32","-ffreestanding","-nostdlib","-fno-pic","-c","kernel.c","-o","kernel.o"],check=True)

    with open("linker.ld","w") as f:
        f.write("ENTRY(_start)\nSECTIONS{. = 1M;.text :{*(.multiboot*)*(.text*)}.data :{*(.data*)}.bss :{*(.bss*)}}")

    subprocess.run([LD,"-m","elf_i386","-T","linker.ld","kernel.o","-o","kernel.elf"],check=True)

    if os.path.exists(ISO_DIR): shutil.rmtree(ISO_DIR)
    os.makedirs("iso/boot/grub",exist_ok=True)
    shutil.copy("kernel.elf","iso/boot/kernel.elf")

    open("iso/boot/grub/grub.cfg","w").write("set timeout=0\nmenuentry \"\" {multiboot /boot/kernel.elf\nboot}")

    subprocess.run(["grub-mkrescue","-o","kernel.iso","iso"],check=True)

    if input("Rodar? s/n: ")=="s":
        subprocess.run([QEMU,"-cdrom","kernel.iso"])

if __name__=="__main__":
    interpretar()
    build()
