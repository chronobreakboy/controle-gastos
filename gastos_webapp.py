import random
import streamlit as st
import pandas as pd
import gspread
from datetime import datetime, timedelta
import json
import os
import smtplib
from email.mime.text import MIMEText
from oauth2client.service_account import ServiceAccountCredentials

SHEET_ID = "1o2WQ0D7Ne-ZkrEXg-Wl5A36LVWFupLioUPalz7F5HmA"
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
    planilha = client.open_by_key(SHEET_ID)
    try:
        return planilha.worksheet(mes_ano)
    except:
        return planilha.add_worksheet(title=mes_ano, rows="1000", cols="10")

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

def calcular_mes_fatura(data_compra, fechamento):
    ano = data_compra.year
    mes = data_compra.month
    if data_compra.day <= fechamento:
        mes_fatura = mes + 1
    else:
        mes_fatura = mes + 2
    if mes_fatura > 12:
        mes_fatura -= 12
        ano += 1
    return datetime(ano, mes_fatura, 1)

def formatar_para_real(texto):
    numeros = "".join(c for c in str(texto) if c.isdigit())
    if not numeros:
        return "", 0.0
    valor_float = int(numeros) / 100
    valor_fmt = (
        f"{valor_float:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )
    return valor_fmt, valor_float

# ---------------------------
# UI
# ---------------------------
st.set_page_config(page_title="Controle de Gastos", layout="centered")
st.title("Controle de Gastos Diários")

usuario = st.selectbox("Quem tá usando?", ["Selecione...", "daddy", "baby girl"])
if usuario == "Selecione...":
    st.stop()

email_juliana = "jucristinegava@gmail.com"
email_robson = "cogumelodosol1@gmail.com"

categorias_gasto_base = [
    "Alimentação", "Bebê", "Beleza", "Casa", "Educação",
    "Lazer", "Pets", "Roupas", "Saúde", "Transporte"
]
categorias_gasto = sorted(categorias_gasto_base) + ["Outros"]
categorias_entrada = ["Salário", "Caixa 2"]

tipo = st.radio("Tipo", ["Gasto", "Entrada"], horizontal=True)
categoria = st.selectbox(
    "Categoria",
    ["Selecione..."] + (categorias_gasto if tipo == "Gasto" else categorias_entrada),
    index=0
)

mensagens_caixa2 = [
    "good girl", "continua assim",
    "minha baby girl maravilhosa", 
    "Minha", 
    "Perfeita",
    "Maravilhosa", 
    "fico todo bobo te vendo assim", 
    "você é tão linda",
    "minha minha minha"
]
descricao_default = random.choice(mensagens_caixa2) if (tipo == "Entrada" and categoria == "Caixa 2") else ""
descricao_disabled = (tipo == "Entrada" and categoria == "Caixa 2")
descricao = st.text_input("Descrição", value=descricao_default, disabled=descricao_disabled)

# ---------------------------
# Campo Valor com MÁSCARA (live) — sem aviso "Press Enter to apply"
# ---------------------------

# Esconde o hint "Press Enter to apply" do input
st.markdown(
    """
    <style>
      .stTextInput [data-baseweb="input"] ~ div { display: none !important; }
    </style>
    """,
    unsafe_allow_html=True
)

# estados do campo
if "valor_value" not in st.session_state:
    st.session_state["valor_value"] = ""      # string formatada exibida no input
if "valor_float" not in st.session_state:
    st.session_state["valor_float"] = 0.0     # número (float) usado no registro

def _fmt_centavos(raw: str):
    if not raw:
        return "", 0.0
    v = int(raw) / 100
    f = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f, v

# input controlado (sem key; controlamos via value)
valor_digitado = st.text_input(
    "Valor",
    value=st.session_state["valor_value"],
    placeholder="0,00",
    max_chars=18,
)

# mantém apenas dígitos, formata e pega float
raw = "".join(c for c in str(valor_digitado) if c.isdigit())
valor_formatado, valor_float = _fmt_centavos(raw)

# se o que está no campo difere do formatado, atualiza estado e rerenderiza
if valor_digitado != valor_formatado:
    st.session_state["valor_value"] = valor_formatado
    st.session_state["valor_float"] = valor_float
    st.rerun()
else:
    st.session_state["valor_value"] = valor_formatado
    st.session_state["valor_float"] = valor_float

# valor numérico final para o restante do app
valor = st.session_state["valor_float"]
if valor_formatado:
    st.caption(f"R$ {valor_formatado}")

credito = False
if tipo == "Gasto":
    credito = st.checkbox("Compra no crédito?")
    if credito:
        cartao = st.selectbox("Cartão", list(cartoes.keys()))
        parcelas = st.slider("Parcelas", 1, 12, 1)

if st.button("Registrar"):
    if categoria == "Selecione..." or not descricao or valor <= 0:
        st.warning("Preencha todos os campos corretamente!")
    else:
        data_compra = datetime.now()
        valor_final = valor if tipo == "Entrada" else -valor
        if tipo == "Entrada" or not credito:
            aba = mes_formatado(data_compra)
            add_lancamento_em_mes(data_compra, descricao, valor_final, categoria, aba)
        else:
            info = cartoes.get(cartao)
            if info:
                fechamento = info["fechamento"]
                mes_fatura = calcular_mes_fatura(data_compra, fechamento)
                valor_parcela = round(valor_final / parcelas, 2)
                for i in range(parcelas):
                    data_parcela = (mes_fatura + pd.DateOffset(months=i)).to_pydatetime()
                    descricao_parcela = f"{descricao} ({i+1}/{parcelas}) - {cartao}"
                    aba = mes_formatado(data_parcela)
                    add_lancamento_em_mes(
                        data_parcela,
                        descricao_parcela,
                        valor_parcela,
                        categoria,
                        aba
                    )
            else:
                st.warning("Cartão sem data configurada.")
        destinatario = email_robson if usuario == "baby girl" else email_juliana
        enviar_email(
            destinatario,
            f"Novo {tipo.lower()} registrado por {usuario}",
            f"{descricao} - R$ {valor_final:.2f} - {categoria}"
        )
        st.success(f"{tipo} registrado com sucesso!")
        st.rerun()

st.subheader("Histórico completo")

def carregar_tudo():
    planilha = client.open_by_key(SHEET_ID)
    abas = planilha.worksheets()
    dados = []
    for aba in abas:
        valores = aba.get_all_values()
        if not valores or valores[0] != ["Data", "Descrição", "Valor (R$)", "Categoria"]:
            continue
        for i in range(1, len(valores)):
            linha = valores[i]
            if len(linha) < 4:
                continue
            try:
                data_obj = datetime.strptime(linha[0], "%d/%m/%Y")
                valor_float = float(str(linha[2]).replace(",", "."))
                dados.append({
                    "Data": linha[0],
                    "Descrição": linha[1],
                    "Valor (R$)": valor_float,
                    "Categoria": linha[3],
                    "DataObj": data_obj,
                    "Aba": aba.title,
                    "LinhaIndex": i - 1
                })
            except:
                continue
    df = pd.DataFrame(dados)
    if not df.empty:
        df = df.sort_values("DataObj", ascending=False).reset_index(drop=True)
    return df

df_historico = carregar_tudo()

if not df_historico.empty:
    aba_atual = mes_formatado(datetime.now())
    total_atual = df_historico[df_historico["Aba"] == aba_atual]["Valor (R$)"].sum()
    st.metric(
        label=f"Saldo total de {aba_atual}",
        value=f"R$ {total_atual:,.2f}".replace(".", "#").replace(",", ".").replace("#", ",")
    )
    for i in df_historico.index:
        col1, col2, col3, col4, col5, col6 = st.columns([2, 3, 2, 3, 2, 1])
        col1.write(df_historico.at[i, "Data"])
        col2.write(df_historico.at[i, "Descrição"])
        valor_hist = df_historico.at[i, "Valor (R$)"]
        col3.write(
            f"R$ {valor_hist:,.2f}".replace(".", "#").replace(",", ".").replace("#", ",")
        )
        col4.write(df_historico.at[i, "Categoria"])
        col5.write(f"Aba: {df_historico.at[i, 'Aba']}")
        if col6.button("🗑️", key=f"delete_global_{i}"):
            aba_nome = df_historico.at[i, "Aba"]
            aba_ws = client.open_by_key(SHEET_ID).worksheet(aba_nome)
            linha_idx = df_historico.at[i, "LinhaIndex"]
            valores_aba = aba_ws.get_all_values()
            linha_planilha = int(linha_idx) + 2
            if 1 < linha_planilha <= len(valores_aba):
                linha_conteudo = valores_aba[linha_planilha - 1]
                if len(linha_conteudo) >= 4 and any(c.strip() for c in linha_conteudo):
                    aba_ws.delete_rows(int(linha_planilha))
                    st.success(f"Registro excluído da aba {aba_nome}!")
                    st.rerun()
                else:
                    st.error("Linha vazia ou incompleta — nada excluído.")
            else:
                st.error(f"Erro: índice inválido para exclusão ({linha_planilha})")
