from tinydb import TinyDB, Query
from werkzeug.security import generate_password_hash
import os

# Cria pasta db se não existir
db_folder = 'db'
if not os.path.exists(db_folder):
    os.makedirs(db_folder)

# Cria o banco TinyDB
db = TinyDB(os.path.join(db_folder, 'erp_viagens.json'))

# Cria tabelas (collections)
usuarios_table = db.table('usuarios')
passageiros_table = db.table('passageiros')
viagens_table = db.table('viagens')
reservas_table = db.table('reservas')

# Insere usuário admin padrão se não existir
User = Query()
if not usuarios_table.search(User.email == 'admin'):
    usuarios_table.insert({
        'email': 'admin',
        'senha': generate_password_hash('admin@admin'),
        'nome': 'Administrador',
        'perfil': 'admin'
    })
    print("Usuário admin criado.")
else:
    print("Usuário admin já existe.")

# Exemplo: insere um passageiro de exemplo
if len(passageiros_table) == 0:
    passageiros_table.insert({
        'nome': 'João Silva',
        'cpf': '000.000.000-00',  # Campo obrigatório para passageiro
        'telefone': '(00) 00000-0000'
    })
    print("Passageiro de exemplo criado.")

# Exemplo: insere uma viagem de exemplo
if len(viagens_table) == 0:
    viagens_table.insert({
        'destino': 'Fortaleza',
        'data': '2025-06-01',
        'preco': 150.0
    })
    print("Viagem de exemplo criada.")

# Exemplo: insere uma reserva de exemplo
if len(reservas_table) == 0:
    reservas_table.insert({
        'id_viagem': 1,  # Aqui poderia ser o doc_id da viagem, ou você pode criar sua lógica
        'id_passageiro': 1,
        'poltrona': '12A',
        'status_pagamento': 'pendente'
    })
    print("Reserva de exemplo criada.")

db.close()
