import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="Sistema de Gestão Mecânica Automotiva (SGMa)", layout="wide", page_icon="🚘")

# --- CONEXÃO COM GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    try:
        return conn.read(ttl=0)
    except:
        # NOVO: Adicionada a coluna 'OS' no DataFrame inicial
        return pd.DataFrame(columns=['OS', 'Data', 'Placa', 'Veículo', 'Serviço', 'Custo (R$)', 'Diagnóstico', 'Responsável'])

# Listas de opções
LISTA_SERVICOS = [
    "Troca de Óleo e Filtro", "Revisão de Freios", "Alinhamento e Balanceamento",
    "Suspensão e Amortecedores", "Sistema Elétrico / Bateria", "Ar-condicionado",
    "Revisão Geral", "Revisão de Lanternagem", "Reparo de Motor", "Outros"
]

LISTA_MECANICOS = ["Jonas Costa", "Rebeca Alves", "Wilson Alves"]

# --- SISTEMA DE LOGIN ---
def autenticacao():
    USUARIOS_PERMITIDOS = {
        "jonascosta": "MENGo2026@", "rebecaalves": "33091221",
        "wilsonalves": "RR2026", "oficina": "oficina123"
    }
    if "logado" not in st.session_state:
        st.session_state.logado = False
    if not st.session_state.logado:
        st.sidebar.title("🔐 Acesso ao Sistema")
        usuario_input = st.sidebar.text_input("Usuário")
        senha_input = st.sidebar.text_input("Senha", type="password")
        if st.sidebar.button("Entrar"):
            if usuario_input in USUARIOS_PERMITIDOS and USUARIOS_PERMITIDOS[usuario_input] == senha_input:
                st.session_state.logado = True
                st.session_state.usuario_nome = usuario_input
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
        
        # --- NOVO: LÓGICA DA OS AUTOMÁTICA ---
        # Se o banco estiver vazio, começa em 1. Se não, pega o último e soma 1.
        if not df.empty and 'OS' in df.columns:
            proxima_os = int(df['OS'].max()) + 1
        else:
            proxima_os = 1
            
        st.info(f"📌 Ordem de Serviço atual: **{proxima_os}**")
        # -------------------------------------
        
        with st.form("form_oficina", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                placa = st.text_input("Placa do Veículo").upper()
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
                    # ALTERADO: Incluído 'proxima_os' na lista de valores
                    nova_linha = pd.DataFrame([[proxima_os, str(data), placa, veiculo, servico, custo, motivo, responsavel]], 
                                             columns=['OS', 'Data', 'Placa', 'Veículo', 'Serviço', 'Custo (R$)', 'Diagnóstico', 'Responsável'])
                    
                    df_final = pd.concat([df, nova_linha], ignore_index=True)
                    conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=df_final)
                    
                    st.success(f"✅ Registro da OS nº {proxima_os} salvo com sucesso!")
                    st.balloons()
                else:
                    st.error("⚠️ Preencha todos os campos obrigatórios.")

    elif escolha == "Histórico e Financeiro":
        st.subheader("🔍 Consulta e Relatório Financeiro")
        if df.empty:
            st.info("Ainda não há registros.")
        else:
            total_geral = df['Custo (R$)'].sum()
            st.metric("Receita Total", f"R$ {total_geral:.2f}")
            
            busca = st.text_input("Buscar por Placa ou OS:").upper()
            if busca:
                # ALTERADO: Busca agora olha tanto para Placa quanto para o número da OS
                resultado = df[(df['Placa'].astype(str).str.contains(busca)) | (df['OS'].astype(str).str.contains(busca))]
                st.dataframe(resultado, use_container_width=True)
            else:
                # Exibe ordenado pela OS mais recente no topo
    
st.dataframe(df.sort_values(by='OS', ascending=False), use_container_width=True)
st.sidebar.markdown("---")
    st.sidebar.caption("VERSÃO 5.1 - 08/04/2026, ÀS 21:46")
