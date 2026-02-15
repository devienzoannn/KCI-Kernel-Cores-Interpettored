// kernel.c

void print(const char* str) {
    while (*str) {
        // Escreve o caractere na tela
        char* video = (char*) 0xB8000;
        *video = *str;
        video[1] = 0x07; // Atributo de cor (branco no preto)
        str++;
    }
}

void kernel_main() {
    
    char* video = (char*) 0xB8000;

    video[0] = 'O';
    video[1] = 0x07;

    video[2] = 'K';
    video[3] = 0x07;

    video[4] = ' ';
    video[5] = 0x07;

    while (1) {
        // Loop infinito
    }
print("Hello, Kernel!");
}
