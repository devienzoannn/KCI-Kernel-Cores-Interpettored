#!/usr/bin/env bash

set -e

echo "==> Atualizando repositórios..."
sudo apt update

echo "==> Instalando toolchain base..."
sudo apt install -y \
    build-essential \
    gcc-multilib \
    binutils \
    xorriso \
    mtools \
    grub-common \
    grub-pc-bin \
    qemu-system-x86

echo "==> Verificando módulos GRUB BIOS..."

if [ -d "/usr/lib/grub/i386-pc" ]; then
    echo "✔ GRUB BIOS modules encontrados."
else
    echo "✖ ERRO: módulos i386-pc não encontrados."
    echo "Instalação incompleta."
    exit 1
fi

echo "==> Verificando suporte 32-bit..."
echo 'int main(){}' > test.c
gcc -m32 test.c -o test32 2>/dev/null || {
    echo "✖ GCC 32-bit não está funcionando."
    rm -f test.c
    exit 1
}
rm -f test.c test32
echo "✔ GCC 32-bit OK."

echo "==> Ambiente pronto para desenvolvimento de kernel."
echo "Use: qemu-system-i386 -kernel kernel.elf"
