import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="SGM - Oficina Pro", layout="wide", page_icon="💰")

ARQUIVO_DADOS = "manutencoes.csv"

# Listas de opções
LISTA_SERVICOS = [
    "Troca de Óleo e Filtro",
    "Revisão de Freios",
    "Alinhamento e Balanceamento",
    "Suspensão e Amortecedores",
    "Sistema Elétrico / Bateria",
    "Ar-condicionado",
    "Revisão Geral",
    "Outros (Detalhar)"
]

LISTA_MECANICOS = ["João Silva", "Ricardo Souza", "Ana Costa", "Carlos Oliveira"]

# --- FUNÇÕES DE DADOS ---
def carregar_dados():
    if os.path.exists(ARQUIVO_DADOS):
        return pd.read_csv(ARQUIVO_DADOS)
    else:
        return pd.DataFrame(columns=['Data', 'Placa', 'Veículo', 'Serviço', 'Custo (R$)', 'Diagnóstico', 'Responsável'])

# --- SISTEMA DE LOGIN ---
def autenticacao():
    if "logado" not in st.session_state:
        st.session_state.logado = False

    if not st.session_state.logado:
        st.sidebar.title("Acesso Restrito")
        usuario = st.sidebar.text_input("Usuário")
        senha = st.sidebar.text_input("Senha", type="password")
        if st.sidebar.button("Entrar"):
            # Usuário e senha para o seu trabalho
            if usuario == "oficina" and senha == "12345":
                st.session_state.logado = True
                st.rerun()
            else:
                st.sidebar.error("Usuário ou senha inválidos")
        st.warning("Por favor, faça login no menu lateral para acessar o sistema.")
        return False
    return True

# --- EXECUÇÃO DO SISTEMA ---
if autenticacao():
    st.title("🔧 Gestão de Manutenção e Custos")
    
    # Botão de Logout no topo da barra lateral
    if st.sidebar.button("Sair/Logout"):
        st.session_state.logado = False
        st.rerun()

    menu = ["Registrar Novo Serviço", "Histórico e Financeiro"]
    escolha = st.sidebar.selectbox("Navegação:", menu)

    df = carregar_dados()

    if escolha == "Registrar Novo Serviço":
        st.subheader("📝 Nova Ordem de Serviço")
        
        with st.form("form_oficina", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                placa = st.text_input("Placa do Veículo").upper()
                veiculo = st.text_input("Modelo/Marca")
                responsavel = st.selectbox("Mecânico Responsável", LISTA_MECANICOS)
            
            with col2:
                data = st.date_input("Data", datetime.now())
                servico = st.selectbox("Serviço Realizado", LISTA_SERVICOS)
                # NOVO CAMPO: Custo do reparo
                custo = st.number_input("Custo Total do Reparo (R$)", min_value=0.0, step=10.0, format="%.2f")
            
            motivo = st.text_area("Diagnóstico e Detalhes")
            
            enviar = st.form_submit_button("Salvar Registro")
            
            if enviar:
                if placa and veiculo and motivo:
                    nova_linha = pd.DataFrame([[data, placa, veiculo, servico, custo, motivo, responsavel]], 
                                             columns=['Data', 'Placa', 'Veículo', 'Serviço', 'Custo (R$)', 'Diagnóstico', 'Responsável'])
                    
                    df = pd.concat([df, nova_linha], ignore_index=True)
                    df.to_csv(ARQUIVO_DADOS, index=False)
                    st.success(f"✅ Registro salvo! Valor: R$ {custo:.2f}")
                else:
                    st.error("Preencha todos os campos obrigatórios.")

    elif escolha == "Histórico e Financeiro":
        st.subheader("🔍 Consulta de Histórico e Custos")
        
        if df.empty:
            st.info("Nenhum dado registrado.")
        else:
            # Resumo Financeiro simples para o Supervisor
            total_geral = df['Custo (R$)'].sum()
            st.metric("Total Acumulado em Reparos", f"R$ {total_geral:.2f}")
            
            busca = st.text_input("Filtrar por Placa:").upper()
            if busca:
                resultado = df[df['Placa'].str.contains(busca)]
                st.dataframe(resultado, use_container_width=True)
            else:
                st.dataframe(df.sort_values(by='Data', ascending=False), use_container_width=True)
