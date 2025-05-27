from fastapi import FastAPI, Form, Request
from fastapi.responses import (
    HTMLResponse,
    RedirectResponse,
    JSONResponse,
    StreamingResponse,
)
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from tinydb import TinyDB, Query, where
import qrcode
from io import BytesIO
import base64
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import os, io, json
from uuid import uuid4
from datetime import datetime, timedelta
import pdfkit
from fastapi.staticfiles import StaticFiles
from PIL import Image
from tinydb import TinyDB

db = TinyDB("database/db.json")
usuarios_table = db.table("usuarios")
passageiros_table = db.table("passageiros")
reservas_table = db.table("reservas")
viagens_table = db.table("viagens")


empresa_table = db.table("empresa")
# empresa = empresa_table.all()
# dados_empresa = empresa[0] if empresa else {}


def gerar_logo_base64(caminho_logo: str) -> str:
    img = Image.open(caminho_logo)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")


def carregar_empresa():
    try:
        with open("database/db.json", "r", encoding="utf-8") as f:
            return json.load().get("empresa", {})
    except:
        return {}


from starlette.middleware.base import BaseHTTPMiddleware


class EmpresaMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        empresa_table = db.table("empresa")
        dados_empresa = empresa_table.all()[0] if empresa_table.all() else None

        response = await call_next(request)
        return response


app.add_middleware(EmpresaMiddleware)
# Caminho do executável wkhtmltopdf
PDFKIT_CONFIG = pdfkit.configuration(
    wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
)


# db = TinyDB("database/db.json")
# usuarios_table = db.table("usuarios")
# passageiros_table = db.table("passageiros")
# reservas_table = db.table("reservas")
# viagens_table = db.table("viagens")
# dados_empresa =db.table("empresa")

CAMINHO_BANCO = "database/db.json"


# Função para carregar banco
def carregar_banco():
    if not os.path.exists(CAMINHO_BANCO):
        return None
    with open(CAMINHO_BANCO, "r", encoding="utf-8") as f:
        try:
            db = json.load(f)
            return db
        except json.JSONDecodeError:
            return None


print("✅ Arquivo carregado com sucesso.")

# CONFIGURAÇÃO ADMIN DO SISTEMA NO BD
DB_PATH = "database/db.json"
# Configuração banco
db = TinyDB(DB_PATH)


def image_to_base64(path):
    import base64

    with open(path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()


# logo_base64 = image_to_base64("static/logo.png")
logo_base64 = gerar_logo_base64("static/logo.png")

# html = templates.get_template("pdf_carne.html").render(
#     venda=venda,
#     parcelas=parcelas,
#     parcelas_valores=parcelas_valores,
#     vencimentos=vencimentos,
#     logo_base64=logo_base64
# )


def carregar_dados():
    if (
        not os.path.exists("database/db.json")
        or os.stat("database/db.json").st_size == 0
    ):
        return {"viagens": [], "passageiros": [], "reservas": [], "usuarios": []}
    with open("database/db.json", "r", encoding="utf-8") as f:
        return json.load(f)


def salvar_dados(db, caminho_arquivo="database/db.json"):
    with open(caminho_arquivo, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4, ensure_ascii=False)


# Verifica e cria usuário admin se não existir
usuarios_table = db.table("usuarios")
User = Query()
if not usuarios_table.contains(User.email == "admin@erp.com"):
    usuarios_table.insert(
        {
            "email": "admin@erp.com",
            "nome": "Administrador",
            "senha": "admin@admin",
            "perfil": "admin",
        }
    )

passageiros_table = db.table("passageiros")
passageiros = db.table("passageiros")

from urllib.parse import quote_plus
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")

# Adiciona o filtro urlencode
templates.env.filters["urlencode"] = lambda u: quote_plus(u)


app.add_middleware(
    SessionMiddleware, secret_key="0000"
)  # Troque a chave por algo seguro em produção

templates = Jinja2Templates(directory="templates")

# Banco de dados
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(
    BASE_DIR, "database", "db.json"
)  # Garante caminho correto em qualquer SO
db = TinyDB(DB_PATH)


# def next_id(table):
#     dados = table.all()
#     return max([d.get("id", 0) for d in dados], default=0) + 1


# --- ROTAS BÁSICAS ---


@app.get("/", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login", response_class=HTMLResponse)
def fazer_login(request: Request, email: str = Form(...), senha: str = Form(...)):
    usuarios = db.table("usuarios").all()
    for usuario in usuarios:
        if usuario["email"] == email and usuario["senha"] == senha:
            request.session["usuario"] = {"email": usuario["email"]}
            return RedirectResponse("/painel", status_code=302)
    # Em caso de erro, retorna o template com mensagem
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "erro": "Usuário ou senha inválidos", "email": email},
    )


# Rota GET para exibir o formulário criar usuário
@app.get("/criar-usuario", response_class=HTMLResponse)
async def criar_usuario_form(request: Request):
    return templates.TemplateResponse(
        "criar_usuario.html", {"request": request, "erro": None}
    )


# Rota POST para criar usuário
@app.post("/criar-usuario", response_class=HTMLResponse)
async def criar_usuario(
    request: Request,
    email: str = Form(...),
    nome: str = Form(...),
    senha: str = Form(...),
    senha_admin: str = Form(...),
):
    # Buscar usuário admin no banco
    User = Query()
    admin_user = usuarios_table.get(User.email == "admin@erp.com")

    if not admin_user:
        return templates.TemplateResponse(
            "criar_usuario.html",
            {"request": request, "erro": "Usuário admin não encontrado."},
        )

    # Validar senha do admin (sem hash)
    if admin_user["senha"] != senha_admin:
        return templates.TemplateResponse(
            "criar_usuario.html",
            {"request": request, "erro": "Senha do administrador inválida."},
        )

    # Verificar se email já existe
    existing_user = usuarios_table.get(User.email == email)
    if existing_user:
        return templates.TemplateResponse(
            "criar_usuario.html", {"request": request, "erro": "E-mail já cadastrado."}
        )

    # Inserir usuário novo
    usuarios_table.insert(
        {
            "email": email,
            "nome": nome,
            "senha": senha,
            "perfil": "usuario",  # perfil padrão
        }
    )

    return RedirectResponse(url="/login", status_code=303)


@app.get("/esqueci-senha", response_class=HTMLResponse)
def form_esqueci_senha(request: Request):
    return templates.TemplateResponse("esqueci_senha.html", {"request": request})


@app.post("/esqueci-senha", response_class=HTMLResponse)
def redefinir_senha(
    request: Request,
    email: str = Form(...),
    nova_senha: str = Form(...),
    admin_senha: str = Form(...),
):
    usuarios = db.table("usuarios")
    admin = usuarios.get(Query().email == "admin@erp.com")

    if not admin or admin["senha"] != admin_senha:
        return templates.TemplateResponse(
            "esqueci_senha.html",
            {"request": request, "erro": "Senha do administrador inválida"},
        )

    if not usuarios.contains(Query().email == email):
        return templates.TemplateResponse(
            "esqueci_senha.html", {"request": request, "erro": "Usuário não encontrado"}
        )

    usuarios.update({"senha": nova_senha}, Query().email == email)
    return RedirectResponse("/login", status_code=302)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()  # Remove os dados da sessão
    return RedirectResponse("/login", status_code=302)


from datetime import datetime


# ----------DADOS EMPRESA-------------
@app.get("/empresa")
def form_empresa(request: Request):
    empresa = db.table("empresa").all()
    return templates.TemplateResponse(
        "cadastrarEmpresa.html",
        {"request": request, "empresa": empresa[0] if empresa else None},
    )


@app.post("/empresa")
def salvar_empresa(
    request: Request,
    nome: str = Form(...),
    telefone: str = Form(...),
    cnpj: str = Form(""),
    endereco: str = Form(""),
    email: str = Form(""),
):
    empresa_table = db.table("empresa")
    empresa_table.truncate()  # só uma empresa
    empresa_table.insert(
        {
            "nome": nome,
            "telefone": telefone,
            "cnpj": cnpj,
            "endereco": endereco,
            "email": email,
        }
    )
    return RedirectResponse("/empresa", status_code=303)


@app.get("/painel", response_class=HTMLResponse)
async def painel(request: Request):
    if "usuario" not in request.session:
        return RedirectResponse("/login", status_code=302)

    db = TinyDB("database/db.json")

    usuarios_table = db.table("usuarios")
    passageiros_table = db.table("passageiros")
    reservas_table = db.table("reservas")
    vendas_table = db.table("vendas")
    viagens_table = db.table("viagens")
    empresa_table = db.table("empresa")

    total_usuarios = len(usuarios_table.all())
    total_passageiros = len(passageiros_table.all())

    # IDs válidos de viagens
    viagens = viagens_table.all()
    ids_viagens_validas = {v.get("id") for v in viagens if v.get("id")}

    # Contar reservas apenas de viagens válidas
    reservas = reservas_table.all()
    total_reservas = 0
    for r in reservas:
        if r.get("id_viagem") in ids_viagens_validas:
            total_reservas += 1  # Cada reserva ocupa uma única poltrona

    total_vendas = len(vendas_table.all())

    empresa_data = empresa_table.all()
    dados_empresa = empresa_data[0] if empresa_data else {}

    hoje = datetime.now().date()
    viagens_proximas = []

    for v in viagens:
        try:
            data_saida = datetime.strptime(v["data_saida"], "%Y-%m-%d").date()
            hora_saida = datetime.strptime(v["hora_saida"], "%H:%M").time()
            v["data_completa"] = datetime.combine(data_saida, hora_saida)
            if data_saida >= hoje:
                viagens_proximas.append(v)
        except:
            continue

    viagens_ordenadas = sorted(viagens_proximas, key=lambda x: x["data_completa"])

    return templates.TemplateResponse(
        "painel.html",
        {
            "request": request,
            "total_usuarios": total_usuarios,
            "total_passageiros": total_passageiros,
            "total_reservas": total_reservas,
            "total_vendas": total_vendas,
            "viagens_proximas": viagens_ordenadas[:5],
            "empresa": dados_empresa,
        },
    )

# --- PASSAGEIROS ---
# Configuração DB (supondo que já tenha configurado antes)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "db.json")
db = TinyDB(DB_PATH)
passageiros_table = db.table("passageiros")


# def next_id(table):
#     dados = table.all()
#     return max([d.get("id", 0) for d in dados], default=0) + 1


@app.get("/novo_passageiro", response_class=HTMLResponse)
def novo_passageiro_form(request: Request):
    return templates.TemplateResponse("novo_passageiro.html", {"request": request})


from pydantic import BaseModel


class PassageiroIn(BaseModel):
    nome: str
    cpf: str
    telefone: str


@app.post("/passageiros/novo")
async def novo_passageiro(request: Request):
    dados = await request.json()

    db_path = os.path.join("database", "db.json")
    db = TinyDB(db_path)
    passageiros_table = db.table("passageiros")

    # Gera novo ID baseado nos existentes
    # registros = passageiros_table.all()
    # if registros:
    #     novo_id = max(int(p["id"]) for p in registros if "id" in p) + 1
    # else:
    #     novo_id = 1

    passageiro = {
        "id": str(uuid4()),  # ← Aqui o UUID único
        "nome": dados.get("nome"),
        "cpf": dados.get("cpf"),
        "telefone": dados.get("telefone"),
    }

    passageiros_table.insert(passageiro)

    return JSONResponse(
        {"success": True, "mensagem": "Passageiro cadastrado com sucesso!"}
    )


@app.get("/passageiros", response_class=HTMLResponse)
def listar_passageiros(request: Request):
    if "usuario" not in request.session:
        return RedirectResponse("/login", status_code=302)

    tabela = db.table("passageiros")
    passageiros = [{**p, "id": p.doc_id} for p in tabela]

    return templates.TemplateResponse(
        "listar_passageiros.html", {"request": request, "passageiros": passageiros}
    )


@app.get("/passageiros/novo", response_class=HTMLResponse)
def novo_passageiro_form(request: Request):
    if "usuario" not in request.session:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("novo_passageiro.html", {"request": request})


@app.post("/passageiros")
def cadastrar_passageiro(
    request: Request,
    nome: str = Form(...),
    documento: str = Form(...),
    telefone: str = Form(...),
):
    if "usuario" not in request.session:
        return RedirectResponse("/login", status_code=302)
    passageiros = db.table("passageiros")
    novo = {
        "id": str(uuid4()),  # ← Aqui o UUID único
        "nome": nome,
        "documento": documento,
        "telefone": telefone,
    }
    passageiros.insert(novo)
    return RedirectResponse("/passageiros", status_code=302)


# EXCLUIR PASSAGEIROS
from fastapi import HTTPException


@app.post("/passageiros/excluir/{passageiro_id}")
async def excluir_passageiro(request: Request, passageiro_id: int):
    if "usuario" not in request.session:
        return JSONResponse(
            {"success": False, "error": "Não autorizado"}, status_code=401
        )

    resultado = passageiros_table.remove(doc_ids=[passageiro_id])

    if resultado:
        return JSONResponse({"success": True})
    else:
        return JSONResponse({"success": False, "error": "Passageiro não encontrado"})


@app.get("/passageiros/editar/{id}", response_class=HTMLResponse)
def editar_passageiro_form(request: Request, id: int):
    if "usuario" not in request.session:
        return RedirectResponse("/login", status_code=302)
    passageiro = db.table("passageiros").get(Query().id == id)
    if not passageiro:
        return RedirectResponse("/passageiros", status_code=302)
    return templates.TemplateResponse(
        "editar_passageiro.html", {"request": request, "passageiro": passageiro}
    )


@app.post("/passageiros/editar/{id}")
def editar_passageiro(
    request: Request,
    id: int,
    nome: str = Form(...),
    documento: str = Form(...),
    telefone: str = Form(...),
):
    if "usuario" not in request.session:
        return RedirectResponse("/login", status_code=302)
    db.table("passageiros").update(
        {"nome": nome, "documento": documento, "telefone": telefone}, Query().id == id
    )
    return RedirectResponse("/passageiros", status_code=302)


# --- VIAGENS ---


@app.get("/viagens", response_class=HTMLResponse)
def listar_viagens(request: Request):
    if "usuario" not in request.session:
        return RedirectResponse("/login", status_code=302)
    viagens = db.table("viagens").all()
    return templates.TemplateResponse(
        "listar_viagens.html", {"request": request, "viagens": viagens}
    )


@app.get("/viagens/nova", response_class=HTMLResponse)
def nova_viagem_form(request: Request):
    if "usuario" not in request.session:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("nova_viagem.html", {"request": request})


@app.post("/viagens")
def cadastrar_viagem(
    request: Request,
    origem: str = Form(...),
    destino: str = Form(...),
    data_saida: str = Form(...),
    hora_saida: str = Form(...),
    preco: float = Form(...),
):
    if "usuario" not in request.session:
        return RedirectResponse("/login", status_code=302)
    viagens = db.table("viagens")
    nova = {
        "id": str(uuid4()),  # ← Aqui o UUID único
        "origem": origem,
        "destino": destino,
        "data_saida": data_saida,
        "hora_saida": hora_saida,
        "preco": preco,
    }
    viagens.insert(nova)
    return RedirectResponse("/viagens", status_code=302)


db = TinyDB("database/db.json")
viagens_table = db.table("viagens")


from pydantic import BaseModel
from typing import Optional


class ViagemIn(BaseModel):
    origem: str
    destino: str
    data_saida: str
    hora_saida: str
    preco: float
    total_poltronas: int


# def next_id(table):
#     registros = [item["id"] for item in table.all() if "id" in item]
#     return max(registros) + 1 if registros else 1


@app.post("/viagens/nova")
async def criar_viagem(request: Request):
    dados = await request.json()

    db_path = os.path.join("database", "db.json")
    db = TinyDB(db_path)
    viagens_table = db.table("viagens")

    # # Gera novo ID
    # registros = viagens_table.all()
    # if registros:
    #     novo_id = max(int(item["id"]) for item in registros if "id" in item) + 1
    # else:
    #     novo_id = 1

    # Lê lista de paradas, ou usa lista vazia se não enviada
    paradas = dados.get("paradas", [])

    nova_viagem = {
        "id": str(uuid4()),  # ← Aqui o UUID único
        "origem": dados.get("origem"),
        "destino": dados.get("destino"),
        "data_saida": dados.get("data_saida"),
        "hora_saida": dados.get("hora_saida"),
        "preco": float(dados.get("preco")),
        "total_poltronas": int(dados.get("total_poltronas")),
        "poltronas_ocupadas": [],
        "paradas": paradas,
    }

    viagens_table.insert(nova_viagem)
    return JSONResponse({"success": True, "mensagem": "Viagem cadastrada com sucesso!"})


db = TinyDB("database/db.json")
viagens_table = db.table("viagens")
templates = Jinja2Templates(directory="templates")


@app.get("/viagens/excluir/{id}")
async def excluir_viagem(request: Request, id: str):
    if "usuario" not in request.session:
        return RedirectResponse("/login", status_code=302)

    db = TinyDB("database/db.json")
    viagens_table = db.table("viagens")
    reservas_table = db.table("reservas")

    # Remove a viagem com o ID fornecido
    viagens_table.remove(where("id") == id)

    # Remove todas as reservas associadas a essa viagem
    reservas_table.remove(where("id_viagem") == id)

    return RedirectResponse("/viagens", status_code=302)


@app.post("/viagens/excluir/{viagem_id}")
async def excluir_viagem_post(viagem_id: str):
    caminho_banco = "database/db.json"
    if not os.path.exists(caminho_banco):
        return JSONResponse(
            content={"success": False, "error": "Banco de dados não encontrado."},
            status_code=404,
        )

    with open(caminho_banco, "r", encoding="utf-8") as f:
        try:
            db = json.load(f)
        except json.JSONDecodeError:
            return JSONResponse(
                content={"success": False, "error": "Erro ao ler o banco de dados."},
                status_code=500,
            )

    viagens = db.get("viagens", {})
    reservas = db.get("reservas", {})

    # Encontra a chave da viagem com o id (UUID) informado
    chave_para_excluir = None
    for k, v in viagens.items():
        if v.get("id") == viagem_id:
            chave_para_excluir = k
            break

    if not chave_para_excluir:
        return JSONResponse(
            content={"success": False, "error": "Viagem não encontrada."},
            status_code=404,
        )

    # Exclui a viagem
    del viagens[chave_para_excluir]

    # Exclui as reservas vinculadas a essa viagem
    reservas = {
        rid: r for rid, r in reservas.items() if r.get("id_viagem") != viagem_id
    }

    db["viagens"] = viagens
    db["reservas"] = reservas

    with open(caminho_banco, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4, ensure_ascii=False)

    return JSONResponse(content={"success": True})


@app.get("/viagens/editar/{id}", response_class=HTMLResponse)
def editar_viagem_form(request: Request, id: str):
    if "usuario" not in request.session:
        return RedirectResponse("/login", status_code=302)
    viagem = db.table("viagens").get(Query().id == id)
    if not viagem:
        return RedirectResponse("/viagens", status_code=302)
    return templates.TemplateResponse(
        "editar_viagem.html", {"request": request, "viagem": viagem}
    )


@app.post("/viagens/editar/{id}")
def editar_viagem(
    request: Request,
    id: str,
    origem: str = Form(...),
    destino: str = Form(...),
    data_saida: str = Form(...),
    hora_saida: str = Form(...),
    preco: float = Form(...),
):
    if "usuario" not in request.session:
        return RedirectResponse("/login", status_code=302)
    db.table("viagens").update(
        {
            "origem": origem,
            "destino": destino,
            "data_saida": data_saida,
            "hora_saida": hora_saida,
            "preco": preco,
        },
        Query().id == id,
    )
    return RedirectResponse("/viagens", status_code=302)


# --- RESERVAS ---


@app.get("/reservas", response_class=HTMLResponse)
async def listar_reservas(request: Request):
    caminho_db = "database/db.json"

    if not os.path.exists(caminho_db):
        return templates.TemplateResponse(
            "erro.html",
            {"request": request, "mensagem": "Banco de dados não encontrado."},
        )

    with open(caminho_db, "r", encoding="utf-8") as f:
        try:
            db = json.load(f)
        except json.JSONDecodeError:
            return templates.TemplateResponse(
                "erro.html",
                {"request": request, "mensagem": "Erro ao ler o banco de dados."},
            )

    reservas_raw = db.get("reservas", {})
    passageiros = db.get("passageiros", {})
    viagens = db.get("viagens", {})

    reservas = []
    destinos = set()

    for reserva in reservas_raw.values():
        id_viagem = str(reserva["id_viagem"])
        id_passageiro = str(reserva["id_passageiro"])

        viagem = next((v for v in viagens.values() if v["id"] == id_viagem), None)
        passageiro = next(
            (p for p in passageiros.values() if p["id"] == id_passageiro), None
        )

        if viagem and passageiro:
            data_saida_str = viagem.get("data_saida", "")
            try:
                data_saida = datetime.strptime(data_saida_str, "%Y-%m-%d")
            except ValueError:
                data_saida = datetime.max  # fallback se a data estiver errada

            reservas.append(
                {
                    "id": reserva["id"],
                    "passageiro": passageiro["nome"],
                    "poltrona": reserva["poltrona"],
                    "destino": viagem["destino"],
                    "data_saida": data_saida,
                }
            )
            destinos.add(viagem["destino"])

    # Ordenar reservas pela data de saída (mais próximas primeiro)
    reservas.sort(key=lambda r: r["data_saida"])

    return templates.TemplateResponse(
        "listar_reservas.html",
        {"request": request, "reservas": reservas, "destinos": sorted(destinos)},
    )


from uuid import UUID


@app.get("/reserva/{id_viagem}", response_class=HTMLResponse)
def tela_reserva(request: Request, id_viagem: str):  # ← era int
    if "usuario" not in request.session:
        return RedirectResponse("/login", status_code=302)
    reservas = db.table("reservas").search(Query().id_viagem == id_viagem)
    passageiros = db.table("passageiros").all()
    ocupadas = [r["poltrona"] for r in reservas]
    poltronas = [
        {"numero": i, "status": "ocupada" if i in ocupadas else "livre"}
        for i in range(1, 51)
    ]
    return templates.TemplateResponse(
        "reserva.html",
        {
            "request": request,
            "id_viagem": id_viagem,
            "poltronas": poltronas,
            "passageiros": passageiros,
        },
    )


@app.get("/mapa-poltronas/{id_viagem}")
def mapa_poltronas(id_viagem: str):  # ← era int
    reservas = db.table("reservas").search(Query().id_viagem == id_viagem)
    ocupadas = [r["poltrona"] for r in reservas]
    mapa = [f"{i:02d} {'🟥' if i in ocupadas else '🟩'}" for i in range(1, 51)]
    return {"mapa": mapa}


@app.post("/reservar")
def reservar_poltrona(
    request: Request,
    id_viagem: str = Form(...),  # ← era int
    id_passageiro: str = Form(...),  # ← era int se estiver usando UUID também aqui
    poltrona: int = Form(...),
):
    if "usuario" not in request.session:
        return RedirectResponse("/login", status_code=302)
    reservas = db.table("reservas")
    if any(
        r["poltrona"] == poltrona
        for r in reservas.search(Query().id_viagem == id_viagem)
    ):
        return JSONResponse(content={"erro": "Poltrona ocupada!"}, status_code=400)
    nova_reserva = {
        "id": str(uuid4()),
        "id_viagem": id_viagem,
        "id_passageiro": id_passageiro,
        "poltrona": poltrona,
        "status_pagamento": "pendente",
    }
    reservas.insert(nova_reserva)
    return JSONResponse(
        {"success": True, "redirect": f"/reserva/confirmada/{nova_reserva['id']}"}
    )


@app.get("/reserva/confirmada/{reserva_id}", response_class=HTMLResponse)
def resumo_reserva(request: Request, reserva_id: str):  # ← era int
    if "usuario" not in request.session:
        return RedirectResponse("/login", status_code=302)

    reservas = db.table("reservas")
    passageiros = db.table("passageiros")
    viagens = db.table("viagens")

    reserva = reservas.get(Query().id == reserva_id)
    if not reserva:
        return RedirectResponse("/reservas", status_code=302)

    passageiro = passageiros.get(Query().id == reserva["id_passageiro"])
    viagem = viagens.get(Query().id == reserva["id_viagem"])

    chave_pix = "pix@empresa.com"
    valor = viagem["preco"]
    descricao = f"Reserva {reserva_id} - {passageiro['nome']}"
    payload = f"Chave PIX: {chave_pix}\nValor: R${valor:.2f}\nDescrição: {descricao}"

    qr = qrcode.make(payload)
    buffer = BytesIO()
    qr.save(buffer)
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    return templates.TemplateResponse(
        "resumo_reserva.html",
        {
            "request": request,
            "reserva": reserva,
            "passageiro": passageiro,
            "viagem": viagem,
            "qr_code": qr_base64,
            "chave_pix": chave_pix,
            "valor": valor,
        },
    )


@app.post("/reservas/excluir/{reserva_id}")
def excluir_reserva(request: Request, reserva_id: str):  # ← era int
    if "usuario" not in request.session:
        return RedirectResponse("/login", status_code=302)
    reservas = db.table("reservas")
    reservas.remove(Query().id == reserva_id)
    return JSONResponse(content={"success": True, "id": reserva_id})


@app.get("/reservas/editar/{id}", response_class=HTMLResponse)
def editar_reserva_form(request: Request, id: str):  # ← era int
    if "usuario" not in request.session:
        return RedirectResponse("/login", status_code=302)
    reserva = db.table("reservas").get(Query().id == id)
    passageiros = db.table("passageiros").all()
    viagens = db.table("viagens").all()
    if not reserva:
        return RedirectResponse("/reservas", status_code=302)
    return templates.TemplateResponse(
        "editar_reserva.html",
        {
            "request": request,
            "reserva": reserva,
            "passageiros": passageiros,
            "viagens": viagens,
        },
    )


@app.post("/reservas/editar/{id}")
def editar_reserva(
    request: Request,
    id: str,  # ← era int
    id_viagem: str = Form(...),
    id_passageiro: str = Form(...),
    poltrona: int = Form(...),
    status_pagamento: str = Form(...),
):
    if "usuario" not in request.session:
        return RedirectResponse("/login", status_code=302)
    reservas = db.table("reservas")
    reservas.update(
        {
            "id_viagem": id_viagem,
            "id_passageiro": id_passageiro,
            "poltrona": poltrona,
            "status_pagamento": status_pagamento,
        },
        Query().id == id,
    )
    return RedirectResponse("/reservas", status_code=302)


# Carrega passageiros da viagem


# Rota: listar passageiros da viagem selecionada
@app.get("/viagens/{viagem_id}/passageiros", response_class=HTMLResponse)
async def listar_passageiros_por_viagem(request: Request, viagem_id: str):
    db = carregar_banco()
    if db is None:
        return templates.TemplateResponse(
            "erro.html",
            {
                "request": request,
                "mensagem": "Banco de dados não encontrado ou inválido.",
            },
        )

    viagens = db.get("viagens", {})
    passageiros = db.get("passageiros", {})
    reservas = db.get("reservas", {})

    # Buscar a viagem pelo id UUID
    viagem = next((v for v in viagens.values() if v["id"] == viagem_id), None)

    if not viagem:
        return templates.TemplateResponse(
            "erro.html", {"request": request, "mensagem": "Viagem não encontrada."}
        )

    passageiros_da_viagem = []

    for reserva in reservas.values():
        if reserva.get("id_viagem") == viagem_id:
            id_passageiro = reserva.get("id_passageiro")
            passageiro = next(
                (p for p in passageiros.values() if p["id"] == id_passageiro), None
            )
            if passageiro:
                p_copy = passageiro.copy()
                p_copy["poltrona"] = reserva.get("poltrona")
                passageiros_da_viagem.append(p_copy)

    # 🔽 Ordenar pela poltrona
    passageiros_da_viagem.sort(key=lambda x: x["poltrona"])

    return templates.TemplateResponse(
        "listarPassageiros.html",
        {
            "request": request,
            "viagem": viagem,
            "passageiros": passageiros_da_viagem,
        },
    )


from fastapi.responses import FileResponse
import pandas as pd
from fpdf import FPDF


@app.get("/viagens/{viagem_id}/passageiros/exportar")
async def exportar_passageiros_pdf(viagem_id: str, formato: str = "pdf"):
    caminho_banco = "database/db.json"
    if not os.path.exists(caminho_banco):
        raise HTTPException(status_code=404, detail="Banco de dados não encontrado.")

    with open(caminho_banco, "r", encoding="utf-8") as f:
        db = json.load(f)

    viagens = db.get("viagens", {})
    passageiros = db.get("passageiros", {})
    reservas = db.get("reservas", {})

    # Buscar viagem pelo ID UUID
    viagem = next((v for v in viagens.values() if v.get("id") == viagem_id), None)
    if not viagem:
        raise HTTPException(status_code=404, detail="Viagem não encontrada.")

    # Lista de passageiros com poltrona
    passageiros_da_viagem = []
    for reserva in reservas.values():
        if reserva.get("id_viagem") == viagem_id:
            passageiro = next(
                (
                    p
                    for p in passageiros.values()
                    if p.get("id") == reserva.get("id_passageiro")
                ),
                None,
            )
            if passageiro:
                passageiros_da_viagem.append(
                    {
                        "poltrona": reserva.get("poltrona"),
                        "nome": passageiro.get("nome", ""),
                        "cpf": passageiro.get("cpf", ""),
                    }
                )

    # Ordena por número da poltrona
    passageiros_da_viagem.sort(key=lambda x: x["poltrona"])

    if formato == "pdf":
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # Cabeçalho do relatório
        p.setFont("Helvetica-Bold", 16)
        p.drawString(
            50, height - 50, f"Passageiros - {viagem['origem']} ➜ {viagem['destino']}"
        )
        p.setFont("Helvetica", 12)
        p.drawString(
            50,
            height - 70,
            f"Data: {viagem['data_saida']}    Hora: {viagem['hora_saida']}",
        )

        y = height - 100

        # Títulos da tabela
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, y, "Poltrona")
        p.drawString(120, y, "Nome")
        p.drawString(350, y, "CPF")
        y -= 20
        p.setFont("Helvetica", 12)

        # Conteúdo
        for passageiro in passageiros_da_viagem:
            if y < 50:
                p.showPage()
                y = height - 50
                p.setFont("Helvetica-Bold", 12)
                p.drawString(50, y, "Poltrona")
                p.drawString(120, y, "Nome")
                p.drawString(350, y, "CPF")
                y -= 20
                p.setFont("Helvetica", 12)

            p.drawString(50, y, str(passageiro["poltrona"]))
            p.drawString(120, y, passageiro["nome"])
            p.drawString(350, y, passageiro["cpf"])
            y -= 20

        p.save()
        buffer.seek(0)

        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=passageiros_viagem_{viagem_id}.pdf"
            },
        )

    raise HTTPException(status_code=400, detail="Formato não suportado.")


@app.get("/documentos", response_class=HTMLResponse)
async def documentos(request: Request):
    return templates.TemplateResponse("document_generator.html", {"request": request})


def listar_vendas():
    return db.table("vendas").all()


# def gerar_id_tinydb(tabela):
#     registros = db.table(tabela).all()
#     if not registros:
#         return 1
#     return max(int(r.get("id", 0)) for r in registros) + 1


# Página de vendas
@app.get("/vendas", response_class=HTMLResponse)
async def pagina_vendas(request: Request):
    passageiros = db.table("passageiros").all()
    viagens = db.table("viagens").all()
    reservas = db.table("reservas").all()
    vendas = db.table("vendas").all()
    return templates.TemplateResponse(
        "vendas.html",
        {
            "request": request,
            "passageiros": passageiros,
            "viagens": viagens,
            "reservas": reservas,
            "vendas": vendas,
        },
    )


# Registrar venda
@app.post("/vendas", response_class=HTMLResponse)
async def registrar_venda(
    request: Request,
    cliente: str = Form(...),
    pacote: str = Form(...),
    quantidade: int = Form(...),
    valor_total: float = Form(...),
):
    venda = {
        "id": str(uuid4()),  # ← Aqui o UUID único
        "cliente": cliente,
        "pacote": pacote,
        "quantidade": quantidade,
        "valor_total": valor_total,
        "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    db.table("vendas").insert(venda)
    return RedirectResponse(url="/vendas", status_code=303)


# Finalizar venda com pagamento
# @app.post("/vendas/finalizar", response_class=HTMLResponse)
# async def finalizar_venda(
#     request: Request,
#     venda_id: str = Form(...),
#     forma_pagamento: str = Form(...),
#     parcelas: int = Form(None),
# ):
#     vendas = db.table("vendas")
#     venda = next((v for v in vendas.all() if v["id"] == venda_id), None)
#     if not venda:
#         return HTMLResponse("Venda não encontrada", status_code=404)

#     venda["forma_pagamento"] = forma_pagamento
#     if forma_pagamento == "boleto" and parcelas:
#         venda["parcelas"] = parcelas

#     vendas.update(
#         venda, doc_ids=[v.doc_id for v in vendas.search(lambda r: r["id"] == venda_id)]
#     )
#     return RedirectResponse(url="/vendas", status_code=303)


# ---------- FINALIZA VENDA------

import uuid


@app.post("/vendas/finalizar-ajax")
async def finalizar_venda_ajax(request: Request):
    form_data = await request.form()

    cliente = form_data.get("cliente")
    pacote = form_data.get("pacote")
    quantidade = int(form_data.get("quantidade", 1))
    valor_total = float(form_data.get("valor_total"))
    forma_pagamento = form_data.get("forma_pagamento")
    parcelas = int(
        form_data.get("parcelas", 1)
    )  # <- IMPORTANTE: Captura do número de parcelas

    nova_venda = {
        "id": str(uuid4()),  # ← Aqui o UUID único
        "cliente": cliente,
        "pacote": pacote,
        "quantidade": quantidade,
        "valor_total": valor_total,
        "forma_pagamento": forma_pagamento,
        "parcelas": parcelas,
        "data": datetime.now().strftime("%d/%m/%Y"),
    }

    db.table("vendas").insert(nova_venda)

    return JSONResponse({"status": "ok", "venda_id": nova_venda["id"]})


@app.get("/vendas/{venda_id}/carne/exportar", response_class=HTMLResponse)
async def exibir_carne(request: Request, venda_id: str):
    vendas_table = db.table("vendas")
    venda = next((v for v in vendas_table.all() if v.get("id") == venda_id), None)

    if not venda:
        raise HTTPException(status_code=404, detail="Venda não encontrada")

    if venda.get("forma_pagamento") != "carne":
        return HTMLResponse("<h3>Venda não foi feita por carnê.</h3>")

    try:
        parcelas = int(venda.get("parcelas", 1))
        valor_total = float(venda.get("valor_total", 0))
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Dados inválidos na venda.")

    # Gera os valores das parcelas com arredondamento correto
    valor_parcela = round(valor_total / parcelas, 2)
    parcelas_valores = [valor_parcela] * parcelas

    soma = round(sum(parcelas_valores), 2)
    diferenca = round(valor_total - soma, 2)
    parcelas_valores[-1] += diferenca  # Corrige última parcela

    # Gera vencimentos mensais (30 dias corridos)
    hoje = datetime.today()
    vencimentos = [
        (hoje + timedelta(days=30 * i)).strftime("%d/%m/%Y") for i in range(parcelas)
    ]

    return templates.TemplateResponse(
        "carne.html",
        {
            "request": request,
            "venda": venda,
            "parcelas": parcelas,
            "parcelas_valores": parcelas_valores,
            "vencimentos": vencimentos,
        },
    )


@app.get("/vendas/{venda_id}/carne/pdf")
async def gerar_pdf_carne(venda_id: str, request: Request):
    vendas_table = db.table("vendas")
    venda = next((v for v in vendas_table.all() if v.get("id") == venda_id), None)

    if not venda:
        return {"error": "Venda não encontrada"}

    parcelas = int(venda.get("parcelas", 1))
    valor_total = float(venda.get("valor_total", 0))
    parcelas_valores = [round(valor_total / parcelas, 2)] * parcelas
    vencimentos = ["2025-06-%02d" % (10 + i) for i in range(parcelas)]  # ou datetime

    # Gerar QR Code do link de pagamento ou info da venda
    qr_data = f"Pagamento Venda: {venda_id} - Valor total: R$ {valor_total:.2f}"
    qr_img = qrcode.make(qr_data)
    buffered = io.BytesIO()
    qr_img.save(buffered, format="PNG")
    qr_base64 = base64.b64encode(buffered.getvalue()).decode()

    html_content = templates.get_template("pdf_carne.html").render(
        request=request,
        venda=venda,
        parcelas=parcelas,
        parcelas_valores=parcelas_valores,
        vencimentos=vencimentos,
        qr_code_base64=qr_base64,
        logo_url="http://localhost:8000/static/logo.png",  # ou outro link externo
        empresa={
            "nome": "Viagem MZ",
            "cnpj": "12.345.678/0001-90",
            "endereco": "Av. das Viagens, 123 - Centro",
            "telefone": "(88) 99999-0000",
            "email": "contato@viagemmz.com",
        },
        data_emissao=datetime.today().strftime("%d/%m/%Y"),
    )

    os.makedirs("temp", exist_ok=True)
    output_path = f"temp/carne_{venda_id}.pdf"

    options = {
        "enable-local-file-access": None,
    }

    pdfkit.from_string(
        html_content, output_path, options=options, configuration=PDFKIT_CONFIG
    )

    return FileResponse(
        output_path, media_type="application/pdf", filename=f"carne_{venda_id}.pdf"
    )


@app.post("/vendas/excluir")
async def excluir_vendas(request: Request):
    form = await request.form()
    venda_ids = form.getlist("venda_ids")

    if venda_ids:
        db_vendas = TinyDB("database/db.json").table("vendas")
        for vid in venda_ids:
            db_vendas.remove(where("id") == vid)

    return RedirectResponse(url="/vendas", status_code=303)


@app.post("/viagens/excluir-multiplas")
async def excluir_varias_viagens(request: Request):
    form = await request.form()
    ids = form.getlist("viagem_ids")

    if not ids:
        return RedirectResponse("/viagens", status_code=303)

    viagens_tb = db.table("viagens")

    for vid in ids:
        viagens_tb.remove(where("id") == vid)  # sem int()

    return RedirectResponse("/viagens", status_code=303)
