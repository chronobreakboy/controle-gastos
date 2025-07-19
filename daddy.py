import streamlit as st
import pandas as pd
import gspread
from datetime import datetime
import json, os
import smtplib
from email.mime.text import MIMEText
from oauth2client.service_account import ServiceAccountCredentials

usuario = "daddy"
email_destino = "jucristinegava@gmail.com"

SHEET_URL = "https://docs.google.com/spreadsheets/d/1o2WQ0D7Ne-ZkrEXg-Wl5A36LVWFupLioUPalz7F5HmA/edit?hl=pt-br"
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.environ["credentials"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open_by_url(SHEET_URL).sheet1

def enviar_email(para, assunto, corpo):
    user = st.secrets["email_user"]
    senha = st.secrets["email_pass"]
    msg = MIMEText(corpo, "plain", "utf-8")
    msg["Subject"] = assunto
    msg["From"] = user
    msg["To"] = para
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(user, senha)
        server.sendmail(user, para, msg.as_string())

def garantir_cabecalho():
    headers = ["Data", "Descrição", "Valor (R$)", "Categoria"]
    todas = sheet.get_all_values()
    if not todas or headers not in todas:
        sheet.insert_row(headers, index=1)

garantir_cabecalho()

def get_dataframe():
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    if not df.empty and "Valor (R$)" in df.columns:
        df["Valor (R$)"] = pd.to_numeric(df["Valor (R$)"], errors="coerce").fillna(0)
    return df

def add_lancamento(data, descricao, valor, categoria):
    valor_str = f"{valor:.2f}".replace(",", ".")
    sheet.append_row([data, descricao, valor_str, categoria])

def excluir_linha(index):
    sheet.delete_rows(index + 2)

st.set_page_config(page_title="Daddy 💸", layout="centered")
st.title("💸 Controle de Gastos - Daddy 💸")

categorias_gasto_base = ["Alimentação", "Bebê", "Beleza", "Casa", "Educação", "Lazer", "Pets", "Roupas", "Saúde", "Transporte"]
categorias_gasto = sorted(categorias_gasto_base) + ["Outros"]
categorias_entrada = ["Salário", "Caixa 2"]

tipo = st.radio("Tipo", ["Gasto", "Entrada"], horizontal=True)
categoria = st.selectbox("Categoria", ["Selecione..."] + (categorias_gasto if tipo == "Gasto" else categorias_entrada), index=0)

descricao_default = "🥵🥵🥵🥵 minha putinha perfeita 🤤🤤🤤🤤🤤" if tipo == "Entrada" and categoria == "Caixa 2" else ""
descricao_disabled = tipo == "Entrada" and categoria == "Caixa 2"
descricao = st.text_input("Descrição", value=descricao_default, disabled=descricao_disabled)
valor = st.number_input("Valor", step=0.01, format="%.2f")

if st.button("Registrar"):
    if categoria == "Selecione..." or not descricao or valor == 0:
        st.warning("Preencha todos os campos corretamente!")
    else:
        sinal = 1 if tipo == "Entrada" else -1
        valor_final = round(valor * sinal, 2)
        data = datetime.now().strftime("%d/%m/%Y")
        add_lancamento(data, descricao, valor_final, categoria)
        st.success(f"{tipo} registrada com sucesso!")
        enviar_email(email_destino, "Novo gasto registrado pelo Robson", f"{descricao} - R$ {valor:.2f} - {categoria}")
        st.rerun()

df = get_dataframe()
if not df.empty:
    st.subheader("📋 Últimos lançamentos")
    for i in df.tail(10).index:
        col1, col2, col3, col4, col5 = st.columns([2, 3, 2, 3, 1])
        col1.write(df.at[i, "Data"])
        col2.write(df.at[i, "Descrição"])
        valor = pd.to_numeric(df.at[i, 'Valor (R$)'], errors='coerce')
        col3.write(f"R$ {valor:,.2f}".replace('.', '#').replace(',', '.').replace('#', ','))
        col4.write(df.at[i, "Categoria"])
        if col5.button("🗑️", key=f"delete_{i}"):
            excluir_linha(i)
            st.success("Registro excluído com sucesso!")
            st.rerun()

    total = df["Valor (R$)"].sum()
    saldo_formatado = f"R$ {total:,.2f}".replace('.', '#').replace(',', '.').replace('#', ',') if pd.notnull(total) else "R$ 0,00"
    st.metric("💰 Saldo atual", saldo_formatado)
