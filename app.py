import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="SGM - Oficina Pro", layout="wide", page_icon="🚘")

# Mudei o nome do arquivo para evitar o erro de coluna inexistente (KeyError)
ARQUIVO_DADOS = "oficina_v3.csv"

# Listas de opções para o formulário
LISTA_SERVICOS = [
    "Troca de Óleo e Filtro",
    "Revisão de Freios",
    "Alinhamento e Balanceamento",
    "Suspensão e Amortecedores",
    "Sistema Elétrico / Bateria",
    "Ar-condicionado",
    "Revisão Geral",
    "Reparo de Motor",
    "Outros (Detalhar no Diagnóstico)"
]

LISTA_MECANICOS = ["João Silva", "Ricardo Souza", "Ana Costa", "Carlos Oliveira"]

# --- FUNÇÕES DE DADOS ---
def carregar_dados():
    if os.path.exists(ARQUIVO_DADOS):
        return pd.read_csv(ARQUIVO_DADOS)
    else:
        # Cria o arquivo do zero com a coluna 'Custo (R$)' incluída
        return pd.DataFrame(columns=['Data', 'Placa', 'Veículo', 'Serviço', 'Custo (R$)', 'Diagnóstico', 'Responsável'])

# --- SISTEMA DE LOGIN ---
# --- SISTEMA DE LOGIN MULTI-USUÁRIO ---
def autenticacao():
    # Defina aqui os usuários permitidos: "usuario": "senha"
    USUARIOS_PERMITIDOS = {
        "jonascosta": "MENGo2026@",
        "rebecaalves": "33091221",
        "wilsonalves": "RR2026",
        "oficina": "oficina123"
    }

    if "logado" not in st.session_state:
        st.session_state.logado = False

    if not st.session_state.logado:
        st.sidebar.title("🔐 Acesso ao Sistema")
        usuario_input = st.sidebar.text_input("Usuário")
        senha_input = st.sidebar.text_input("Senha", type="password")
        
        if st.sidebar.button("Entrar"):
            # Verifica se o usuário existe e se a senha está correta
            if usuario_input in USUARIOS_PERMITIDOS and USUARIOS_PERMITIDOS[usuario_input] == senha_input:
                st.session_state.logado = True
                st.session_state.usuario_nome = usuario_input # Guarda quem logou
                st.rerun()
            else:
                st.sidebar.error("Usuário ou senha inválidos")
        return False
    return True

# --- EXECUÇÃO DO SISTEMA ---
if autenticacao():
    st.title("🔧 Gestão de Manutenção e Custos")
    
    if st.sidebar.button("Sair / Logout"):
        st.session_state.logado = False
        st.rerun()

    menu = ["Registrar Novo Serviço", "Histórico e Financeiro"]
    escolha = st.sidebar.selectbox("Menu de Navegação:", menu)

    df = carregar_dados()

    if escolha == "Registrar Novo Serviço":
        st.subheader("📝 Registrar Ordem de Serviço")
        
        with st.form("form_oficina", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                placa = st.text_input("Placa do Veículo (Ex: ABC1234)").upper()
                veiculo = st.text_input("Modelo/Marca")
                responsavel = st.selectbox("Mecânico Responsável", LISTA_MECANICOS)
            
            with col2:
                data = st.date_input("Data do Serviço", datetime.now())
                servico = st.selectbox("Serviço Realizado", LISTA_SERVICOS)
                custo = st.number_input("Custo Total (R$)", min_value=0.0, step=50.0, format="%.2f")
            
            motivo = st.text_area("Diagnóstico (Por que foi feito?)")
            
            enviar = st.form_submit_button("Salvar Manutenção")
            
            if enviar:
                if placa and veiculo and motivo:
                    nova_linha = pd.DataFrame([[data, placa, veiculo, servico, custo, motivo, responsavel]], 
                                             columns=['Data', 'Placa', 'Veículo', 'Serviço', 'Custo (R$)', 'Diagnóstico', 'Responsável'])
                    
                    # Salva no CSV
                    df = pd.concat([df, nova_linha], ignore_index=True)
                    df.to_csv(ARQUIVO_DADOS, index=False)
                    st.success(f"✅ Registro da placa {placa} salvo com sucesso!")
                    st.balloons()
                else:
                    st.error("⚠️ Por favor, preencha Placa, Veículo e Diagnóstico.")

    elif escolha == "Histórico e Financeiro":
        st.subheader("🔍 Consulta e Relatório Financeiro")
        
        if df.empty:
            st.info("Ainda não há registros no novo banco de dados (oficina_v3).")
        else:
            # Painel Financeiro
            total_geral = df['Custo (R$)'].sum()
            col_metric, _ = st.columns([1, 2])
            with col_metric:
                st.metric("Receita Total de Reparos", f"R$ {total_geral:.2f}")
            
            st.write("---")
            
            # Filtro de busca
            busca = st.text_input("Buscar por Placa:").upper()
            if busca:
                resultado = df[df['Placa'].str.contains(busca)]
                st.dataframe(resultado, use_container_width=True)
            else:
                st.dataframe(df.sort_values(by='Data', ascending=False), use_container_width=True)

    st.sidebar.markdown("---")
    st.sidebar.caption("Versão 3.0")
