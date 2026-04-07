import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Sistema Oficina Pro", layout="wide")

st.title("🔧 Gestão de Manutenção - Oficina")

# Menu Lateral
menu = ["Registrar Manutenção", "Histórico de Veículos"]
escolha = st.sidebar.selectbox("Menu", menu)

if escolha == "Registrar Manutenção":
    st.subheader("📝 Novo Registro")
    
    with st.form("form_manutencao"):
        col1, col2 = st.columns(2)
        with col1:
            placa = st.text_input("Placa do Veículo")
            veiculo = st.text_input("Modelo/Marca")
            responsavel = st.selectbox("Mecânico Responsável", ["João Silva", "Ricardo Souza", "Ana Costa"])
        
        with col2:
            data = st.date_input("Data do Serviço", datetime.now())
            servico = st.text_area("O que foi feito?")
            motivo = st.text_area("Por que foi feito? (Diagnóstico)")
            
        botao = st.form_submit_button("Salvar Registro")
        
        if botao:
            st.success(f"Manutenção da placa {placa} registrada com sucesso!")
            # Aqui entraria o código para salvar no Google Sheets ou CSV local

elif escolha == "Histórico de Veículos":
    st.subheader("🔍 Consultar Histórico")
    busca = st.text_input("Digite a Placa para buscar")
    
    # Exemplo de como os dados aparecem
    dados_exemplo = pd.DataFrame({
        'Data': ['2026-04-01'],
        'Placa': ['ABC-1234'],
        'Serviço': ['Troca de Pastilhas'],
        'Motivo': ['Desgaste natural / Ruído ao frear']
    })
    st.table(dados_exemplo)