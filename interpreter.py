import os
import shutil
import subprocess

# ==============================
# CONFIG
# ==============================
GCC = "gcc"
LD = "ld"
QEMU = "qemu-system-i386"
ISO_DIR = "iso"

generated_functions = ""
generated_main = ""
inside_function = False

# ==============================
# TEMPLATE DO KERNEL
# ==============================
KERNEL_TEMPLATE_START = r"""
#include <stdint.h>

__attribute__((section(".multiboot"), used))
const uint32_t multiboot_header[] = {
    0x1BADB002,
    0x00000000,
    0xE4524FFE
};

typedef unsigned short u16;
u16* video = (u16*)0xB8000;
int cursor = 0;

void kprint(const char* str) {
    int i = 0;
    while (str[i]) {
        video[cursor++] = (0x0F << 8) | str[i++];
    }
}

/* ==== FUNÇÕES GERADAS ==== */
"""

KERNEL_TEMPLATE_MIDDLE = r"""

void _start() {

/* ==== CÓDIGO GERADO ==== */
"""

KERNEL_TEMPLATE_END = r"""

    while (1) { __asm__("hlt"); }
}
"""

# ==============================
# COMANDOS .kci
# ==============================
def cmd_print(args):
    global generated_functions, generated_main, inside_function
    text = " ".join(args).replace('"', '\\"')
    line = f'    kprint("{text}\\n");\n'

    if inside_function:
        generated_functions += line
    else:
        generated_main += line


def cmd_func(args):
    global generated_functions, inside_function
    name = args[0]
    generated_functions += f"\nvoid {name}() {{\n"
    inside_function = True


def cmd_raw(args):
    global generated_functions, generated_main, inside_function
    line = " ".join(args)

    if inside_function:
        generated_functions += f"    {line}\n"
    else:
        generated_main += f"    {line}\n"


def cmd_end(args):
    global generated_functions, inside_function
    generated_functions += "}\n"
    inside_function = False

def cmd_delay(args):
    global generated_code
    seconds = int(args[0])
    loops = seconds * 100_000_000
    generated_code += f"""
    for (volatile int i = 0; i < {loops}; i++) {{
        __asm__("nop");
    }}
"""



COMMANDS = {
    "print": cmd_print,
    "func": cmd_func,
    "raw": cmd_raw,
    "end": cmd_end,
    "delay": cmd_delay,
}

# ==============================
# INTERPRETADOR
# ==============================
def interpretar():
    for file in os.listdir("."):
        if file.endswith(".kci"):
            with open(file) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    parts = line.split()
                    cmd = parts[0]

                    if cmd in COMMANDS:
                        COMMANDS[cmd](parts[1:])
                    else:
                        print(f"Comando desconhecido: {cmd}")

# ==============================
# BUILD
# ==============================
def build():
    # 1. Gerar kernel.c
    print("Gerando kernel.c...")
    with open("kernel.c", "w") as f:
        f.write(KERNEL_TEMPLATE_START)
        f.write(generated_functions)
        f.write(KERNEL_TEMPLATE_MIDDLE)
        f.write(generated_main)
        f.write(KERNEL_TEMPLATE_END)

    # 2. Compilar
    print("Compilando kernel.o...")
    subprocess.run([
        GCC, "-m32", "-ffreestanding",
        "-nostdlib", "-fno-pic",
        "-O0",
        "-c", "kernel.c", "-o", "kernel.o"
    ], check=True)

    # 3. Linker
    print("Criando linker.ld...")
    with open("linker.ld", "w") as f:
        f.write("""ENTRY(_start)

SECTIONS
{
    . = 1M;

    .text : { *(.multiboot*) *(.text*) }
    .rodata : { *(.rodata*) }
    .data : { *(.data*) }
    .bss : { *(COMMON) *(.bss*) }
}
""")

    print("Linkando kernel.elf...")
    subprocess.run([
        LD, "-m", "elf_i386",
"-T", "linker.ld",
"-nostdlib",
"kernel.o",
"-o", "kernel.elf"
    ], check=True)

    # 4. Estrutura ISO
    if os.path.exists(ISO_DIR):
        shutil.rmtree(ISO_DIR)

    os.makedirs(os.path.join(ISO_DIR, "boot", "grub"), exist_ok=True)
    shutil.copy("kernel.elf", os.path.join(ISO_DIR, "boot", "kernel.elf"))

    # 5. grub.cfg
    print("Criando grub.cfg...")
    with open(os.path.join(ISO_DIR, "boot", "grub", "grub.cfg"), "w") as f:
        f.write("""
set timeout=0
set default=0

menuentry "MeuKernel" {
    multiboot /boot/kernel.elf
    boot
}
""")

    # 6. ISO
    print("Gerando ISO...")
    subprocess.run([
        "grub-mkrescue",
        "-o", "kernel.iso",
        ISO_DIR,
        
    ], check=True)

    print("Build finalizado!")

    if input("Rodar no QEMU? (s/n): ").lower() == "s":
        subprocess.run([QEMU, "-cdrom", "kernel.iso"])

# ==============================
# MAIN
# ==============================
if __name__ == "__main__":
    interpretar()
    build()
