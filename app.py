import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="SGM - Oficina Mecânica", layout="wide", page_icon="🔧")

ARQUIVO_DADOS = "manutencoes.csv"

# Listas de opções padronizadas (Otimização do preenchimento)
LISTA_SERVICOS = [
    "Troca de Óleo e Filtro",
    "Revisão de Freios (Pastilhas/Discos)",
    "Alinhamento e Balanceamento",
    "Suspensão e Amortecedores",
    "Sistema Elétrico / Bateria",
    "Ar-condicionado (Carga/Limpeza)",
    "Troca de Correia Dentada",
    "Reparo de Motor",
    "Troca de Pneus",
    "Outros (Detalhar no Diagnóstico)"
]

LISTA_MECANICOS = ["João Silva", "Ricardo Souza", "Ana Costa", "Carlos Oliveira"]

# --- FUNÇÕES DE DADOS ---
def carregar_dados():
    if os.path.exists(ARQUIVO_DADOS):
        return pd.read_csv(ARQUIVO_DADOS)
    else:
        # Cria um DataFrame vazio com as colunas necessárias caso o arquivo não exista
        return pd.DataFrame(columns=['Data', 'Placa', 'Veículo', 'Serviço', 'Diagnóstico/Motivo', 'Responsável'])

# --- INTERFACE ---
st.title("🔧 Sistema de Gestão de Manutenção - Oficina")
st.markdown("---")

# Menu Lateral para Navegação
menu = ["Registrar Novo Serviço", "Histórico de Manutenções"]
escolha = st.sidebar.selectbox("Selecione uma opção:", menu)

df = carregar_dados()

if escolha == "Registrar Novo Serviço":
    st.subheader("📝 Registrar Nova Ordem de Serviço")
    
    with st.form("form_oficina", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            placa = st.text_input("Placa do Veículo (Ex: ABC1234)").upper()
            veiculo = st.text_input("Modelo e Marca do Carro")
            responsavel = st.selectbox("Mecânico Responsável", LISTA_MECANICOS)
        
        with col2:
            data = st.date_input("Data do Registro", datetime.now())
            # AQUI: Substituímos o campo de texto por uma lista selecionável
            servico = st.selectbox("Serviço Realizado", LISTA_SERVICOS)
            motivo = st.text_area("Diagnóstico / Por que foi feito?")
        
        enviar = st.form_submit_button("Salvar Registro no Sistema")
        
        if enviar:
            if placa and veiculo and motivo:
                nova_linha = pd.DataFrame([[data, placa, veiculo, servico, motivo, responsavel]], 
                                         columns=['Data', 'Placa', 'Veículo', 'Serviço', 'Diagnóstico/Motivo', 'Responsável'])
                
                # Concatena e salva no arquivo CSV
                df = pd.concat([df, nova_linha], ignore_index=True)
                df.to_csv(ARQUIVO_DADOS, index=False)
                
                st.success(f"✅ Manutenção do veículo {placa} registrada com sucesso!")
                st.balloons()
            else:
                st.error("⚠️ Por favor, preencha todos os campos obrigatórios.")

elif escolha == "Histórico de Manutenções":
    st.subheader("🔍 Consultar Registros de Manutenção")
    
    if df.empty:
        st.warning("Ainda não existem registros no sistema.")
    else:
        # Filtro de busca por placa para o supervisor
        busca_placa = st.text_input("Filtrar por Placa do Veículo:").upper()
        
        if busca_placa:
            resultado = df[df['Placa'].str.contains(busca_placa)]
            if not resultado.empty:
                st.dataframe(resultado, use_container_width=True)
            else:
                st.info("Nenhum registro encontrado para esta placa.")
        else:
            st.write("Exibindo todos os registros recentes:")
            st.dataframe(df.sort_values(by='Data', ascending=False), use_container_width=True)

# Rodapé simples
st.sidebar.markdown("---")
st.sidebar.info("Projeto Acadêmico - Sistema de Otimização de Oficina")
