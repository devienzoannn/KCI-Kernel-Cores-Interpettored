import os
import sys

pasta = "."


def func_print(args):
    bootloader = f"""
[ORG 0x7C00]
; Código de exemplo para o bootloader
MOV AX, 0x0000
MOV DS, AX
MOV ES, AX
MOV SI, msg
call print_string
JMP $
msg DB '{args.join('')}', 0
print_string:
    MOV AL, [SI]
    OR AL, AL
    JZ .done
    ; Aqui você pode adicionar código para imprimir o caractere em AL
    ; Por exemplo, usando a porta de vídeo ou outra técnica de saída
    INC SI
    JMP print_string
    .done:
    RET
"""

def func_add(args):
    if len(args) < 2:
        print(f"Erro: 'add' precisa de pelo menos 2 argumentos.")
        return
    try:
        resultado = int(args[0]) + int(args[1])
        print("Resultado da soma:", resultado)
    except ValueError:
        print("Erro: argumentos devem ser números.")

# Mapeamento de funções
funcoes = {
    "print": func_print,
    "add": func_add
}

def interpretar(arquivo):
    with open(arquivo, "r") as f:
        for linha in f:
            linha = linha.strip()
            if not linha:
                continue
            partes = linha.split()
            cmd = partes[0]
            args = partes[1:]
            if cmd in funcoes:
                funcoes[cmd](args)
            else:
                print(f"Comando desconhecido: {cmd}")


def main():
    encontrados = False
    for arquivo in os.listdir(pasta):
        if arquivo.endswith(".kci"):
            encontrados = True
            interpretar(arquivo)

    if not encontrados:
        print("Nenhum arquivo KCI encontrado na pasta atual.")
        sys.exit(1)
        

if __name__ == "__main__":
    main()
