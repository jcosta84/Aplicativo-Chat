import streamlit as st
from sqlalchemy import create_engine, text
import pandas as pd
import os
import time
from datetime import datetime

st.set_page_config(page_title="Chat Avançado", layout="wide")

# --- Configuração da conexão SQL Server ---
server = "192.168.38.2,1433"
database = "chat"
username = "instante"
password = "loucoste9309323"
driver = "ODBC Driver 17 for SQL Server"

# Conexão
conn_str = f"mssql+pyodbc://{username}:{password}@{server}/{database}?driver={driver}"
engine = create_engine(conn_str)

# --- Funções auxiliares ---
def autenticar_usuario(nome, senha):
    with engine.begin() as conn:
        user = conn.execute(
            text("SELECT * FROM Usuarios WHERE username=:n AND password=:s"),
            {"n": nome, "s": senha}
        ).fetchone()
    return user is not None

def atualizar_status(nome, status):
    with engine.begin() as conn:
        conn.execute(text("UPDATE Usuarios SET Online=:s WHERE username=:n"), {"s": status, "n": nome})

def listar_usuarios():
    with engine.begin() as conn:
        return pd.read_sql("SELECT username, Online FROM Usuarios", conn)

# --- Estado da sessão ---
if "usuario" not in st.session_state:
    st.session_state.usuario = None

# --- Tela de login ---
if st.session_state.usuario is None:
    st.title("🔑 Login no Chat")
    nome = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if autenticar_usuario(nome, senha):
            st.session_state.usuario = nome
            atualizar_status(nome, 1)  # setar online
            st.success(f"Bem-vindo, {nome}!")
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")
    st.stop()

# --- Sidebar com contatos ---
st.sidebar.title("📨 Contatos")
usuarios = listar_usuarios()
usuarios = usuarios[usuarios["username"] != st.session_state.usuario]  # remover eu mesmo

# Mostrar status online/offline
for _, row in usuarios.iterrows():
    status = "🟢 Online" if row["Online"] else "⚪ Offline"
    st.sidebar.write(f"{row['username']} {status}")

destinatario = st.sidebar.selectbox("Selecione um contato", usuarios["username"].tolist())


# --- Área principal de chat ---
st.title(f"💬 Conversa com {destinatario}")

# Recarregar automaticamente
if st.sidebar.checkbox("🔄 Atualizar automaticamente"):
    time.sleep(5)
    st.rerun()

# Buscar histórico de conversa
with engine.begin() as conn:
    conversa = pd.read_sql(
        text("""
            SELECT Remetente, Destinatario, Mensagem, Anexo, DataEnvio
            FROM Mensagens
            WHERE (Remetente=:u AND Destinatario=:d)
               OR (Remetente=:d AND Destinatario=:u)
            ORDER BY DataEnvio
        """),
        conn,
        params={"u": st.session_state.usuario, "d": destinatario}
    )

# Mostrar chat
if not conversa.empty:
    for _, row in conversa.iterrows():
        if row["Remetente"] == st.session_state.usuario:
            bubble = st.chat_message("user")
        else:
            bubble = st.chat_message("assistant")

        if row["Mensagem"]:
            bubble.write(row["Mensagem"])
        if row["Anexo"]:
            if row["Anexo"].lower().endswith((".png", ".jpg", ".jpeg")):
                bubble.image(row["Anexo"])
            elif row["Anexo"].lower().endswith(".pdf"):
                bubble.write(f"📎 [Abrir PDF]({row['Anexo']})")
            else:
                bubble.write(f"📎 [Baixar arquivo]({row['Anexo']})")
else:
    st.info("Nenhuma mensagem ainda.")

# --- Caixa de envio ---
if "msg_input" not in st.session_state:
    st.session_state.msg_input = ""  # inicializa vazio

with st.sidebar:
    mensagem = st.text_area("Digite sua mensagem", key="msg_input")
    arquivo = st.file_uploader("📎 Anexar", type=["png", "jpg", "jpeg", "pdf"], key="file_upload")

    # --- Enviar mensagem ---
    if st.button("Enviar"):
        caminho_arquivo = None
        if arquivo is not None:
            pasta = "uploads"
            os.makedirs(pasta, exist_ok=True)
            nome_arquivo = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{arquivo.name}"
            caminho_arquivo = os.path.join(pasta, nome_arquivo)
            with open(caminho_arquivo, "wb") as f:
                f.write(arquivo.getbuffer())

        # Inserir mensagem no banco
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO Mensagens (Remetente, Destinatario, Mensagem, Anexo) VALUES (:r, :d, :m, :a)"),
                {"r": st.session_state.usuario, "d": destinatario, "m": mensagem, "a": caminho_arquivo}
            )

        # Limpar a caixa de mensagem e upload automaticamente
        st.rerun()

with st.sidebar:
    st.markdown("---")
    
# Botão de logout
if st.sidebar.button("Sair"):
    atualizar_status(st.session_state.usuario, 0)  # setar offline
    st.session_state.usuario = None
    st.rerun()