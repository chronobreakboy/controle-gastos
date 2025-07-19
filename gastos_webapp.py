import streamlit as st
import pandas as pd
import gspread
from datetime import datetime, timedelta
import json, os
import smtplib
from email.mime.text import MIMEText
from oauth2client.service_account import ServiceAccountCredentials

SHEET_URL = "https://docs.google.com/spreadsheets/d/1o2WQ0D7Ne-ZkrEXg-Wl5A36LVWFupLioUPalz7F5HmA/edit?hl=pt-br"
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.environ["credentials"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

cartoes = {
    "Credz": {"fechamento": 27, "vencimento": 1},
    "Nubank Robson": {"fechamento": 28, "vencimento": 4},
    "PicPay": {"fechamento": 27, "vencimento": 5},
    "C&A": {"fechamento": 25, "vencimento": 8},
    "Renner": None,
    "Shopee": {"fechamento": 31, "vencimento": 10},
    "Pernambucanas": {"fechamento": 6, "vencimento": 11},
    "Mercado Pago": {"fechamento": 9, "vencimento": 14},
    "Palmeiras": {"fechamento": 15, "vencimento": 21},
    "Mais": None,
    "Nubank Juliana": {"fechamento": 20, "vencimento": 27}
}

def obter_aba_mes(mes_ano):
    try:
        return client.open_by_url(SHEET_URL).worksheet(mes_ano)
    except:
        return client.open_by_url(SHEET_URL).add_worksheet(title=mes_ano, rows="1000", cols="10")

def mes_formatado(dt):
    return dt.strftime("%b/%Y").capitalize()

def add_lancamento_em_mes(data, descricao, valor, categoria, aba):
    sheet_mes = obter_aba_mes(aba)
    headers = ["Data", "Descrição", "Valor (R$)", "Categoria"]
    todas = sheet_mes.get_all_values()
    if not todas or todas[0] != headers:
        sheet_mes.insert_row(headers, index=1)
    valor_str = f"{valor:.2f}".replace(",", ".")
    sheet_mes.append_row([data.strftime("%d/%m/%Y"), descricao, valor_str, categoria])

def excluir_linha(sheet_mes, index):
    sheet_mes.delete_rows(index + 2)

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

st.set_page_config(page_title="Controle de Gastos", layout="centered")
st.title("💸 Controle de Gastos Diários 💸")

usuario = st.selectbox("Quem tá usando?", ["Selecione...", "daddy", "baby girl"])
if usuario == "Selecione...": st.stop()

email_juliana = "jucristinegava@gmail.com"
email_robson = "cogumelodosol1@gmail.com"

categorias_gasto_base = ["Alimentação", "Bebê", "Beleza", "Casa", "Educação", "Lazer", "Pets", "Roupas", "Saúde", "Transporte"]
categorias_gasto = sorted(categorias_gasto_base) + ["Outros"]
categorias_entrada = ["Salário", "Caixa 2"]
tipo = st.radio("Tipo", ["Gasto", "Entrada"], horizontal=True)
categoria = st.selectbox("Categoria", ["Selecione..."] + (categorias_gasto if tipo == "Gasto" else categorias_entrada), index=0)
descricao = st.text_input("Descrição")
valor = st.number_input("Valor", step=0.01, format="%.2f")

credito = False
if tipo == "Gasto":
    credito = st.checkbox("Compra no crédito?")
    if credito:
        cartao = st.selectbox("Cartão", list(cartoes.keys()))
        parcelas = st.slider("Parcelas", 1, 18, 1)

if st.button("Registrar"):
    if categoria == "Selecione..." or not descricao or valor == 0:
        st.warning("Preencha todos os campos corretamente!")
    else:
        data_compra = datetime.now()
        if tipo == "Entrada" or not credito:
            aba = mes_formatado(data_compra)
            add_lancamento_em_mes(data_compra, descricao, valor, categoria, aba)
        else:
            info = cartoes.get(cartao)
            if info:
                fechamento = info["fechamento"]
                if data_compra.day > fechamento:
                    primeira_fatura = (data_compra.replace(day=1) + timedelta(days=32)).replace(day=1)
                else:
                    primeira_fatura = data_compra.replace(day=1)
                valor_parcela = round(valor / parcelas, 2)
                for i in range(parcelas):
                    data_parcela = (primeira_fatura + pd.DateOffset(months=i)).to_pydatetime()
                    descricao_parcela = f"{descricao} ({i+1}/{parcelas}) - {cartao}"
                    aba = mes_formatado(data_parcela)
                    add_lancamento_em_mes(data_parcela, descricao_parcela, valor_parcela, categoria, aba)
            else:
                st.warning("Cartão sem data configurada.")
        destinatario = email_robson if usuario == "baby girl" else email_juliana
        enviar_email(destinatario, f"Novo {tipo.lower()} registrado por {usuario}", f"{descricao} - R$ {valor:.2f} - {categoria}")
        st.success(f"{tipo} registrado com sucesso!")
        st.rerun()

# === EXIBE HISTÓRICO DE TODAS AS ABAS ===
st.subheader("📚 Histórico completo")

def carregar_tudo():
    planilha = client.open_by_url(SHEET_URL)
    abas = planilha.worksheets()
    dados = []
    for aba in abas:
        valores = aba.get_all_records()
        for i, linha in enumerate(valores):
            if "Data" in linha and "Valor (R$)" in linha:
                try:
                    data_obj = datetime.strptime(linha["Data"], "%d/%m/%Y")
                    linha["DataObj"] = data_obj
                    linha["Aba"] = aba.title
                    linha["LinhaIndex"] = i
                    dados.append(linha)
                except:
                    continue
    df = pd.DataFrame(dados)
    if not df.empty:
        df = df.sort_values("DataObj", ascending=False).reset_index(drop=True)
    return df

df_historico = carregar_tudo()

if not df_historico.empty:
    for i in df_historico.index:
        col1, col2, col3, col4, col5, col6 = st.columns([2, 3, 2, 3, 2, 1])
        col1.write(df_historico.at[i, "Data"])
        col2.write(df_historico.at[i, "Descrição"])
        valor = pd.to_numeric(df_historico.at[i, 'Valor (R$)'], errors='coerce')
        col3.write(f"R$ {valor:,.2f}".replace('.', '#').replace(',', '.').replace('#', ','))
        col4.write(df_historico.at[i, "Categoria"])
        col5.write(f"Aba: {df_historico.at[i, 'Aba']}")
        if col6.button("🗑️", key=f"delete_global_{i}"):
            aba_nome = df_historico.at[i, "Aba"]
            aba = client.open_by_url(SHEET_URL).worksheet(aba_nome)
            aba.delete_rows(df_historico.at[i, "LinhaIndex"] + 2)
            st.success(f"Registro excluído da aba {aba_nome}!")
            st.rerun()
