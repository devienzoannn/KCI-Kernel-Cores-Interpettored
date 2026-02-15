[ORG 0x7C00]
; Código de exemplo para o bootloader
MOV AX, 0x0000
MOV DS, AX
MOV ES, AX
MOV SI, msg
call print_string
JMP $
msg DB 'Initializing...', 0"""