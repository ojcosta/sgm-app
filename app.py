import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="SGM Automotiva", layout="wide", page_icon="🚘")

# --- CONEXÃO COM GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    try:
        dados = conn.read(ttl=0)
        colunas_necessarias = ['OS', 'Data', 'Placa', 'Veículo', 'Proprietário', 'Serviço', 'Custo (R$)', 'Diagnóstico', 'Responsável']
        
        if dados.empty:
            return pd.DataFrame(columns=colunas_necessarias)
        
        for col in colunas_necessarias:
            if col not in dados.columns:
                dados[col] = None
        return dados
    except:
        return pd.DataFrame(columns=['OS', 'Data', 'Placa', 'Veículo', 'Proprietário', 'Serviço', 'Custo (R$)', 'Diagnóstico', 'Responsável'])

# Listas de opções
LISTA_SERVICOS = [
    "Troca de Óleo e Filtro", "Revisão de Freios", "Alinhamento e Balanceamento",
    "Suspensão e Amortecedores", "Sistema Elétrico / Bateria", "Ar-condicionado",
    "Revisão Geral", "Revisão de Lanternagem", "Reparo de Motor", "Outros (Expecificar)"
]

LISTA_MECANICOS = ["Jonas Costa", "Rebeca Alves", "Wilson Alves"]
LISTA_MARCA = [
    "Fiat", "Volkswagen", "Chevrolet", "Ford", "Renault", "Citroën", "BMW", "Audi", "Nissan", "BYD", "Hyundai", "Toyota", "Honda", "Jeep", "Mercedes-Benz", "Mitsubish", "Infinit", "Jaguar", "Lexus", "Mazda", "Outros (Expecificar)"
]

# --- SISTEMA DE LOGIN REESTRUTURADO ---
def autenticacao():
    USUARIOS_PERMITIDOS = {
        "jonascosta": "MENGo2026@", "rebecaalves": "33091221", "wilsonalves": "RR2026", "oficina": "oficina123", "pedrobueno": "oficina1234"
    }
    
    if "logado" not in st.session_state:
        st.session_state.logado = False

    if not st.session_state.logado:
        # --- Layout da Barra Lateral (Login) ---
        st.sidebar.markdown("# 🔐 Portal SGM")
        st.sidebar.write("Faça login para acessar o painel.")
        
        usuario_input = st.sidebar.text_input("Usuário", placeholder="seu_usuario")
        senha_input = st.sidebar.text_input("Senha", type="password", placeholder="••••••••")
        
        if st.sidebar.button("Entrar no Sistema", use_container_width=True):
            if usuario_input in USUARIOS_PERMITIDOS and USUARIOS_PERMITIDOS[usuario_input] == senha_input:
                st.session_state.logado = True
                st.session_state.usuario_nome = usuario_input
                st.rerun()
            else:
                st.sidebar.error("⚠️ Usuário ou senha inválidos")

        # --- Layout do Corpo Central (Preenchimento Visual) ---
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            # Ícone central para tirar a sensação de vazio
            st.markdown("<h1 style='text-align: center;'>🚘 SGM Automotiva</h1>", unsafe_allow_html=True)
            st.markdown("<h4 style='text-align: center; color: gray;'>Gestão de Manutenção e Custos</h4>", unsafe_allow_html=True)
            
            st.info("""
            **Acesso Restrito.** Para registrar novos serviços ou consultar o histórico financeiro, utilize o formulário de login ao lado.
            """)
            
            # Pequeno Dashboard visual (apenas ilustrativo na tela de login)
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Status", "Online")
            col_b.metric("Versão", "7.2 (Beta)")
            col_c.metric("Suporte", "Ativo")
            
        return False
    return True

# --- EXECUÇÃO DO SISTEMA ---
if autenticacao():
    # Banner de boas-vindas após login
    st.title(f"🔧 Bem-vindo(a)")
    
    if st.sidebar.button("Sair / Logout"):
        st.session_state.logado = False
        st.rerun()

    menu = ["Registrar Novo Serviço", "Histórico e Financeiro"]
    escolha = st.sidebar.selectbox("Menu de Navegação:", menu)

    df = carregar_dados()

    if escolha == "Registrar Novo Serviço":
        st.subheader("📝 Registrar Ordem de Serviço")
        
        try:
            if not df.empty and 'OS' in df.columns:
                proxima_os = int(pd.to_numeric(df['OS'], errors='coerce').max() or 0) + 1
            else:
                proxima_os = 1
        except:
            proxima_os = len(df) + 1
            
        st.info(f"📌 Ordem de Serviço atual: **{proxima_os}**")
        
        with st.form("form_oficina", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                placa = st.text_input("Placa do Veículo").upper()
                marca = st.selectbox("Marca", LISTA_MARCA) # Ajustado variável para não conflitar
                propietario = st.text_input("Proprietário do Veículo")
                responsavel = st.selectbox("Mecânico Responsável", LISTA_MECANICOS)
            with col2:
                data = st.date_input("Data do Serviço", datetime.now())
                modelo = st.text_input("Modelo") # Ajustado variável para clareza
                servico = st.selectbox("Serviço Realizado", LISTA_SERVICOS)
                custo = st.number_input("Custo Total (R$)", min_value=0.0, step=50.0, format="%.2f")
            
            motivo = st.text_area("Diagnóstico")
            
            enviar = st.form_submit_button("Salvar Manutenção")
            
            if enviar:
                if placa and modelo and motivo:
                    nova_linha = pd.DataFrame([[proxima_os, str(data), placa, f"{marca} {modelo}", propietario, servico, custo, motivo, responsavel]], 
                                             columns=['OS', 'Data', 'Placa', 'Veículo', 'Proprietário', 'Serviço', 'Custo (R$)', 'Diagnóstico', 'Responsável'])
                    
                    df_final = pd.concat([df, nova_linha], ignore_index=True)
                    conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=df_final)
                    
                    st.success(f"✅ Registro da OS nº {proxima_os} salvo com sucesso!")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("⚠️ Preencha todos os campos obrigatórios (Placa, Modelo e Diagnóstico).")

    elif escolha == "Histórico e Financeiro":
        st.subheader("🔍 Consulta e Relatório Financeiro")
        if df.empty or len(df.columns) < 2:
            st.info("Ainda não há registros ou a planilha está sendo configurada.")
        else:
            if 'Custo (R$)' in df.columns:
                total_geral = pd.to_numeric(df['Custo (R$)'], errors='coerce').fillna(0).sum()
                st.metric("Receita Total de Reparos", f"R$ {total_geral:.2f}")
            
            st.write("---")
            
            busca = st.text_input("Buscar por Placa ou OS:").upper()
            
            exibir_df = df.copy()
            
            if busca:
                resultado = exibir_df[(exibir_df['Placa'].astype(str).str.contains(busca)) | (exibir_df['OS'].astype(str).str.contains(busca))]
                st.dataframe(resultado, use_container_width=True)
            else:
                if 'OS' in exibir_df.columns:
                    st.dataframe(exibir_df.sort_values(by='OS', ascending=False), use_container_width=True)
                else:
                    st.dataframe(exibir_df, use_container_width=True)

    st.sidebar.markdown("---")
    st.sidebar.caption("Versão 7.2")