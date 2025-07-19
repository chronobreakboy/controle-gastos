import streamlit as st
import pandas as pd
import gspread
from datetime import datetime
import json, os
from oauth2client.service_account import ServiceAccountCredentials

# === CONFIG GOOGLE SHEETS ===
SHEET_URL = "https://docs.google.com/spreadsheets/d/1o2WQ0D7Ne-ZkrEXg-Wl5A36LVWFupLioUPalz7F5HmA/edit?hl=pt-br"
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.environ["credentials"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open_by_url(SHEET_URL).sheet1

# === GARANTIR CABEÇALHO ===
def garantir_cabecalho():
    headers = ["Data", "Descrição", "Valor (R$)", "Categoria"]
    registros = sheet.get_all_records()
    if not registros:
        sheet.insert_row(headers, index=1)
    elif sheet.row_values(1) != headers:
        sheet.delete_rows(1)
        sheet.insert_row(headers, index=1)

garantir_cabecalho()

# === FUNÇÕES AUXILIARES ===
def get_dataframe():
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def add_lancamento(data, descricao, valor, categoria):
    sheet.append_row([data, descricao, valor, categoria])

def excluir_linha(index):
    sheet.delete_rows(index + 2)

# === INTERFACE ===
st.set_page_config(page_title="Controle de Gastos", layout="centered")
st.title("💸 Controle de Gastos Diários 💔")

with st.form("form_gasto"):
    descricao = st.text_input("Descrição")
    valor = st.number_input("Valor (use positivo)", step=0.01, format="%.2f")
    categoria = st.text_input("Categoria")
    tipo = st.radio("Tipo", ["Gasto", "Entrada"])
    enviar = st.form_submit_button("Registrar")

if enviar:
    if descricao and valor != 0 and categoria:
        sinal = 1 if tipo == "Entrada" else -1
        valor_final = round(valor * sinal, 2)
        data = datetime.now().strftime("%d/%m/%Y")
        add_lancamento(data, descricao.capitalize(), valor_final, categoria.capitalize())
        st.success(f"{tipo} registrada com sucesso!")
        st.rerun()
    else:
        st.warning("Preencha todos os campos!")

df = get_dataframe()
if not df.empty:
    st.subheader("📋 Últimos lançamentos")
    for i in df.tail(10).index:
        col1, col2, col3, col4, col5 = st.columns([2, 3, 2, 3, 1])
        col1.write(df.at[i, "Data"])
        col2.write(df.at[i, "Descrição"])
        col3.write(f"R$ {df.at[i, 'Valor (R$)']:.2f}".replace('.', ','))
        col4.write(df.at[i, "Categoria"])
        if col5.button("🗑️", key=f"delete_{i}"):
            excluir_linha(i)
            st.success("Registro excluído com sucesso!")
            st.rerun()

    total = df["Valor (R$)"].sum()
    saldo_formatado = f"R$ {total:,.2f}".replace('.', '#').replace(',', '.').replace('#', ',')
    st.metric("💰 Saldo atual", saldo_formatado)
