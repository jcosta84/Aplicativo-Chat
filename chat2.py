import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
from sqlalchemy import create_engine, text
import pandas as pd
import os
from datetime import datetime

# --- Configurações do banco de dados ---
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

def enviar_mensagem(remetente, destinatario, mensagem, anexo=None):
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO Mensagens (Remetente, Destinatario, Mensagem, Anexo) VALUES (:r, :d, :m, :a)"),
            {"r": remetente, "d": destinatario, "m": mensagem, "a": anexo}
        )

def buscar_mensagens(usuario, contato):
    with engine.begin() as conn:
        df = pd.read_sql(
            text("""
                SELECT Remetente, Destinatario, Mensagem, Anexo, DataEnvio
                FROM Mensagens
                WHERE (Remetente=:u AND Destinatario=:d)
                   OR (Remetente=:d AND Destinatario=:u)
                ORDER BY DataEnvio
            """),
            conn,
            params={"u": usuario, "d": contato}
        )
    return df

# --- Inicialização do app ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

root = ctk.CTk()
root.title("Chat Avançado")
root.geometry("900x600")

# Variáveis globais
usuario = None

# --- Login ---
def tela_login():
    global usuario
    frame_login = ctk.CTkFrame(root)
    frame_login.pack(fill="both", expand=True, padx=20, pady=20)

    ctk.CTkLabel(frame_login, text="🔑 Login no Chat", font=("Arial", 24)).pack(pady=20)
    entry_user = ctk.CTkEntry(frame_login, placeholder_text="Usuário")
    entry_user.pack(pady=10)
    entry_senha = ctk.CTkEntry(frame_login, placeholder_text="Senha", show="*")
    entry_senha.pack(pady=10)

    def login_callback():
        global usuario  # <-- trocar nonlocal por global
        nome = entry_user.get()
        senha = entry_senha.get()
        if autenticar_usuario(nome, senha):
            usuario = nome
            atualizar_status(nome, 1)
            frame_login.destroy()
            tela_chat()
        else:
            messagebox.showerror("Erro", "Usuário ou senha incorretos")

    btn_login = ctk.CTkButton(frame_login, text="Entrar", command=login_callback)
    btn_login.pack(pady=20)

# --- Chat ---
def tela_chat():
    global usuario
    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(1, weight=1)

    # Sidebar de contatos
    frame_sidebar = ctk.CTkFrame(root, width=200)
    frame_sidebar.grid(row=0, column=0, sticky="ns")
    ctk.CTkLabel(frame_sidebar, text="📨 Contatos", font=("Arial", 16)).pack(pady=10)

    lista_usuarios = listar_usuarios()
    lista_usuarios = lista_usuarios[lista_usuarios["username"] != usuario]
    listbox_contatos = tk.Listbox(frame_sidebar)
    listbox_contatos.pack(fill="both", expand=True, padx=10, pady=10)
    for u in lista_usuarios["username"]:
        status = "🟢 Online" if lista_usuarios[lista_usuarios["username"] == u]["Online"].values[0] else "⚪ Offline"
        listbox_contatos.insert(tk.END, f"{u} {status}")

    def logout():
        atualizar_status(usuario, 0)
        root.destroy()

    btn_logout = ctk.CTkButton(frame_sidebar, text="Sair", command=logout)
    btn_logout.pack(pady=10)

    # Frame principal do chat
    frame_chat = ctk.CTkFrame(root)
    frame_chat.grid(row=0, column=1, sticky="nsew")
    frame_chat.grid_rowconfigure(0, weight=1)
    frame_chat.grid_columnconfigure(0, weight=1)

    # Canvas para mensagens
    canvas_chat = tk.Canvas(frame_chat, bg="#1e1e1e")
    scrollbar = tk.Scrollbar(frame_chat, orient="vertical", command=canvas_chat.yview)
    canvas_chat.configure(yscrollcommand=scrollbar.set)
    scrollbar.grid(row=0, column=1, sticky="ns")
    canvas_chat.grid(row=0, column=0, sticky="nsew")

    frame_messages = ctk.CTkFrame(canvas_chat, fg_color="transparent")
    canvas_chat.create_window((0,0), window=frame_messages, anchor="nw")

    def atualizar_chat():
        for widget in frame_messages.winfo_children():
            widget.destroy()
        contato = listbox_contatos.get(tk.ACTIVE)
        if not contato:
            return
        msgs = buscar_mensagens(usuario, contato)
        for _, row in msgs.iterrows():
            remetente = row["Remetente"]
            texto = row["Mensagem"]
            if remetente == usuario:
                lbl = ctk.CTkLabel(frame_messages, text=texto, anchor="e", fg_color="#3b82f6", corner_radius=10)
            else:
                lbl = ctk.CTkLabel(frame_messages, text=texto, anchor="w", fg_color="#525252", corner_radius=10)
            lbl.pack(fill="x", pady=2, padx=5)
        frame_messages.update_idletasks()
        canvas_chat.configure(scrollregion=canvas_chat.bbox("all"))
        canvas_chat.yview_moveto(1.0)

    # Barra inferior fixa
    frame_bottom = ctk.CTkFrame(frame_chat, height=60)
    frame_bottom.grid(row=1, column=0, columnspan=2, sticky="ew")
    frame_bottom.grid_columnconfigure(0, weight=1)

    mensagem_var = tk.StringVar()
    entry_msg = ctk.CTkEntry(frame_bottom, textvariable=mensagem_var)
    entry_msg.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

    arquivo_path_var = tk.StringVar(value="")

    def selecionar_arquivo():
        path = filedialog.askopenfilename(filetypes=[("Arquivos", "*.png *.jpg *.jpeg *.pdf")])
        arquivo_path_var.set(path)

    btn_arquivo = ctk.CTkButton(frame_bottom, text="📎", width=40, command=selecionar_arquivo)
    btn_arquivo.grid(row=0, column=1, padx=5, pady=5)

    def enviar_callback():
        contato = listbox_contatos.get(tk.ACTIVE)
        if not contato:
            messagebox.showwarning("Aviso", "Selecione um contato")
            return
        enviar_mensagem(usuario, contato, mensagem_var.get(), arquivo_path_var.get() if arquivo_path_var.get() else None)
        mensagem_var.set("")
        arquivo_path_var.set("")
        atualizar_chat()

    btn_enviar = ctk.CTkButton(frame_bottom, text="Enviar", command=enviar_callback)
    btn_enviar.grid(row=0, column=2, padx=5, pady=5)

    # Atualizar chat a cada seleção de contato
    def on_select(evt):
        atualizar_chat()

    listbox_contatos.bind("<<ListboxSelect>>", on_select)

    atualizar_chat()

# --- Executar app ---
tela_login()
root.mainloop()
