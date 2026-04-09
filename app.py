import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="Sistema de Gestão Mecânica Automotiva (SGMa)", layout="wide", page_icon="🚘")

# --- CONEXÃO COM GOOGLE SHEETS (Substitui o CSV) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    # ttl=0 garante que ele busque os dados atualizados da planilha sempre
    try:
        return conn.read(ttl=0)
    except:
        # Caso a planilha esteja vazia, cria o cabeçalho padrão
        return pd.DataFrame(columns=['Data', 'Placa', 'Veículo', 'Serviço', 'Custo (R$)', 'Diagnóstico', 'Responsável'])

# Listas de opções para o formulário
LISTA_SERVICOS = [
    "Troca de Óleo e Filtro",
    "Revisão de Freios",
    "Alinhamento e Balanceamento",
    "Suspensão e Amortecedores",
    "Sistema Elétrico / Bateria",
    "Ar-condicionado",
    "Revisão Geral",
    "Revisão de Lanternagem"
    "Reparo de Motor",
    "Outros (Detalhar no Diagnóstico)"
]

LISTA_MECANICOS = ["Jonas Costa", "Rebeca Alves", "Wilson Alves"]

# --- SISTEMA DE LOGIN MULTI-USUÁRIO ---
def autenticacao():
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
                    # Preparando a nova linha (converte data para string para evitar erro no Google)
                    nova_linha = pd.DataFrame([[str(data), placa, veiculo, servico, custo, motivo, responsavel]], 
                                             columns=['Data', 'Placa', 'Veículo', 'Serviço', 'Custo (R$)', 'Diagnóstico', 'Responsável'])
                    
                    # Atualiza a planilha no Google Sheets
                    df_final = pd.concat([df, nova_linha], ignore_index=True)
                    conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=df_final)
                    
                    st.success(f"✅ Registro da placa {placa} salvo na Nuvem com sucesso!")
                    st.balloons()
                else:
                    st.error("⚠️ Por favor, preencha Placa, Veículo e Diagnóstico.")

    elif escolha == "Histórico e Financeiro":
        st.subheader("🔍 Consulta e Relatório Financeiro (Google Sheets)")
        
        if df.empty:
            st.info("Ainda não há registros na planilha.")
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
                resultado = df[df['Placa'].astype(str).str.contains(busca)]
                st.dataframe(resultado, use_container_width=True)
            else:
                st.dataframe(df.sort_values(by='Data', ascending=False), use_container_width=True)

    st.sidebar.markdown("---")
    st.sidebar.caption("Versão 4.0 - Google Sheets Cloud")
