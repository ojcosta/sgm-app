import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="SGM - Oficina", layout="wide")

# Nome do arquivo que guardará os dados
ARQUIVO_DADOS = "manutencoes.csv"

# Função para carregar dados
def carregar_dados():
    if os.path.exists(ARQUIVO_DADOS):
        return pd.read_csv(ARQUIVO_DADOS)
    else:
        return pd.DataFrame(columns=['Data', 'Placa', 'Veículo', 'Serviço', 'Motivo', 'Responsável'])

# Interface
st.title("🔧 Sistema de Gestão de Manutenção (SGM)")

menu = ["Registrar Novo Serviço", "Consultar Histórico Completo"]
escolha = st.sidebar.selectbox("Navegação", menu)

df = carregar_dados()

if escolha == "Registrar Novo Serviço":
    st.subheader("📝 Registrar Manutenção")
    with st.form("form_oficina", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            placa = st.text_input("Placa do Veículo").upper()
            veiculo = st.text_input("Modelo/Marca")
            responsavel = st.text_input("Mecânico Responsável")
        with col2:
            data = st.date_input("Data", datetime.now())
            servico = st.text_area("Descrição do Serviço")
            motivo = st.text_area("Diagnóstico (O Porquê)")
        
        enviar = st.form_submit_button("Salvar no Sistema")
        
        if enviar:
            nova_linha = pd.DataFrame([[data, placa, veiculo, servico, motivo, responsavel]], 
                                     columns=['Data', 'Placa', 'Veículo', 'Serviço', 'Motivo', 'Responsável'])
            # Salva no arquivo CSV
            df = pd.concat([df, nova_linha], ignore_index=True)
            df.to_csv(ARQUIVO_DADOS, index=False)
            st.success("✅ Serviço registrado com sucesso! O histórico foi atualizado.")

elif escolha == "Consultar Histórico Completo":
    st.subheader("🔍 Histórico de Manutenções")
    
    if df.empty:
        st.info("Nenhum registro encontrado.")
    else:
        # Filtro rápido por placa
        filtro = st.text_input("Filtrar por Placa").upper()
        if filtro:
            df_filtrado = df[df['Placa'].str.contains(filtro)]
            st.dataframe(df_filtrado, use_container_width=True)
        else:
            st.dataframe(df, use_container_width=True)
