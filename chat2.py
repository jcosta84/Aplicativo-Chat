import tkinter as tk
from tkinter import simpledialog, filedialog, messagebox, scrolledtext
from sqlalchemy import create_engine, text
import pandas as pd
import os
from datetime import datetime

# --- Conexão com SQL Server ---
server = "192.168.38.2,1433"
database = "chat"
username = "instante"
password = "loucoste9309323"
driver = "ODBC Driver 17 for SQL Server"
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

def buscar_conversa(remetente, destinatario):
    with engine.begin() as conn:
        return pd.read_sql(
            text("""
                SELECT Remetente, Destinatario, Mensagem, Anexo, DataEnvio
                FROM Mensagens
                WHERE (Remetente=:u AND Destinatario=:d)
                   OR (Remetente=:d AND Destinatario=:u)
                ORDER BY DataEnvio
            """),
            conn,
            params={"u": remetente, "d": destinatario}
        )

def enviar_mensagem(remetente, destinatario, mensagem, arquivo_path=None):
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO Mensagens (Remetente, Destinatario, Mensagem, Anexo) VALUES (:r, :d, :m, :a)"),
            {"r": remetente, "d": destinatario, "m": mensagem, "a": arquivo_path}
        )

# --- Login ---
root = tk.Tk()
root.withdraw()  # Oculta janela principal durante login

usuario = simpledialog.askstring("Login", "Usuário:")
senha = simpledialog.askstring("Login", "Senha:", show="*")

if not autenticar_usuario(usuario, senha):
    messagebox.showerror("Erro", "Usuário ou senha incorretos")
    exit()
atualizar_status(usuario, 1)

root.deiconify()  # Mostra janela principal
root.title(f"Chat Avançado - Usuário: {usuario}")
root.geometry("800x600")

# --- Layout ---
frame_contatos = tk.Frame(root, width=200)
frame_contatos.pack(side=tk.LEFT, fill=tk.Y)

frame_chat = tk.Frame(root)
frame_chat.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

# Contatos
tk.Label(frame_contatos, text="Contatos").pack()
usuarios_df = listar_usuarios()
usuarios_list = [u for u in usuarios_df["username"].tolist() if u != usuario]
destinatario_var = tk.StringVar(value=usuarios_list[0] if usuarios_list else "")

listbox = tk.Listbox(frame_contatos, listvariable=tk.StringVar(value=usuarios_list))
listbox.pack(fill=tk.BOTH, expand=True)

# Caixa de chat
chat_text = scrolledtext.ScrolledText(frame_chat)
chat_text.pack(fill=tk.BOTH, expand=True)

mensagem_var = tk.StringVar()

entry_frame = tk.Frame(frame_chat)
entry_frame.pack(fill=tk.X)

entry = tk.Entry(entry_frame, textvariable=mensagem_var)
entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

def enviar_callback():
    destinatario = listbox.get(tk.ACTIVE)
    mensagem = mensagem_var.get()
    arquivo_path = None

    file = filedialog.askopenfilename(title="Selecionar arquivo", 
                                      filetypes=[("Arquivos", "*.png *.jpg *.jpeg *.pdf")])
    if file:
        pasta = "uploads"
        os.makedirs(pasta, exist_ok=True)
        nome_arquivo = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{os.path.basename(file)}"
        arquivo_path = os.path.join(pasta, nome_arquivo)
        with open(file, "rb") as f_in, open(arquivo_path, "wb") as f_out:
            f_out.write(f_in.read())

    enviar_mensagem(usuario, destinatario, mensagem, arquivo_path)
    mensagem_var.set("")
    atualizar_chat()

def atualizar_chat():
    destinatario = listbox.get(tk.ACTIVE)
    conversa_df = buscar_conversa(usuario, destinatario)
    chat_text.delete("1.0", tk.END)
    for _, row in conversa_df.iterrows():
        remetente = row["Remetente"]
        msg = row["Mensagem"]
        chat_text.insert(tk.END, f"{remetente}: {msg}\n")
        if row["Anexo"]:
            chat_text.insert(tk.END, f"📎 {row['Anexo']}\n")
    chat_text.see(tk.END)

enviar_btn = tk.Button(entry_frame, text="Enviar", command=enviar_callback)
enviar_btn.pack(side=tk.RIGHT)

# Atualizar chat ao selecionar outro contato
def contato_selecionado(event):
    atualizar_chat()
listbox.bind("<<ListboxSelect>>", contato_selecionado)

# Atualizar chat a cada 5 segundos
def refresh_loop():
    atualizar_chat()
    root.after(5000, refresh_loop)

refresh_loop()
root.mainloop()
