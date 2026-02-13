import os
import sys

pasta = "."

def interpretar(arquivo, fun_name, codigo_python, min_args=0):
    with open(arquivo, "r") as f:
        for linha in f:
            linha = linha.strip()
            if not linha:
                continue  # pula linhas vazias

            partes = linha.split()
            if partes[0] == fun_name:
                args = partes[1:]

                if len(args) < min_args:
                    print(f"Erro: '{fun_name}' precisa de pelo menos {min_args} argumento(s).")
                    print(f"Linha inválida: {linha}")
                    continue

                # executa código passado pelo main
                exec(codigo_python, {}, {"args": args})


def main():
    encountered = False

    codigo_print = """
print("Executando comando print")
print("Argumentos:", args)
"""

    for arquivo in os.listdir(pasta):
        if arquivo.endswith(".kci"):
            encountered = True
            interpretar(arquivo, "print", codigo_print, min_args=1)
            
            codigo_add = """
print("Executando comando add")
try:
    numeros = list(map(float, args))
    resultado = sum(numeros)
    print("Resultado da soma:", resultado)
"""
            interpretar(arquivo, "add", codigo_add, min_args=2)

    if not encountered:
        print("Nenhum arquivo KCI encontrado na pasta atual.")
        sys.exit(1)


if __name__ == "__main__":
    main()
