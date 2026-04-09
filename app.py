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

# --- LISTAS DE OPÇÕES ---
LISTA_SERVICOS = [
    "Troca de Óleo e Filtro", "Reparo de Freios", "Alinhamento e Balanceamento", "Suspensão e Amortecedores", 
    "Sistema Elétrico", "Ar-condicionado", "Revisão de Lanternagem", "Reparo de Motor", "Revisão Geral", "Outros (Especificar)"
]

LISTA_MECANICOS = ["Jonas Costa", "Rebeca Alves", "Wilson Alves"]
LISTA_MARCA = [
    "Fiat", "Volkswagen", "Chevrolet", "Ford", "Renault", "Citroën", "BMW", "Audi", "Nissan", "BYD", 
    "Hyundai", "Toyota", "Honda", "Jeep", "Mercedes-Benz", "Mitsubish", "Infinit", "Jaguar", "Lexus", "Mazda", "Outros"
]

# --- SISTEMA DE LOGIN ---
def autenticacao():
    USUARIOS_PERMITIDOS = {
        "jonascosta": "MENGo2026@", "rebecaalves": "33091221", "wilsonalves": "RR2026", 
        "oficina": "oficina123", "pedrobueno": "oficina1234"
    }
    
    if "logado" not in st.session_state:
        st.session_state.logado = False

    if not st.session_state.logado:
        st.sidebar.markdown("# 🔐 Portal SGM")
        usuario_input = st.sidebar.text_input("Usuário")
        senha_input = st.sidebar.text_input("Senha", type="password")
        
        if st.sidebar.button("Entrar no Sistema", use_container_width=True):
            if usuario_input in USUARIOS_PERMITIDOS and USUARIOS_PERMITIDOS[usuario_input] == senha_input:
                st.session_state.logado = True
                st.session_state.usuario_nome = usuario_input
                st.rerun()
            else:
                st.sidebar.error("⚠️ Usuário ou senha inválidos")

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown("<h1 style='text-align: center;'>🚘 SGM Automotiva</h1>", unsafe_allow_html=True)
            st.info("**Acesso Restrito.** Use o painel lateral para entrar.")
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Status", "Online")
            c2.metric("Versão", "9.0")
            c3.metric("Suporte", "Ativo")
            
        return False
    return True

# --- EXECUÇÃO DO SISTEMA ---
if autenticacao():
    st.sidebar.write(f"Logado como: **{st.session_state.usuario_nome}**")
    if st.sidebar.button("Sair / Logout"):
        st.session_state.logado = False
        st.rerun()

    menu = ["Registrar Novo Serviço", "Histórico e Financeiro", "Sobre o APP"]
    escolha = st.sidebar.selectbox("Menu de Navegação:", menu)

    df = carregar_dados()

    if escolha == "Registrar Novo Serviço":
        st.subheader("📝 Registrar Ordem de Serviço")
        
        try:
            proxima_os = int(pd.to_numeric(df['OS'], errors='coerce').max() or 0) + 1
        except:
            proxima_os = len(df) + 1
            
        st.info(f"📌 Ordem de Serviço atual: **{proxima_os}**")
        
        with st.form("form_oficina", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                data = st.date_input("Data do Serviço", datetime.now())
                marca = st.selectbox("Marca", LISTA_MARCA)
                propietario = st.text_input("Proprietário do Veículo")
                custo = st.number_input("Custo Total (R$)", min_value=0.0, step=10.0, format="%.2f")
            with col2:
                responsavel = st.selectbox("Mecânico Responsável", LISTA_MECANICOS)
                modelo = st.text_input("Modelo e Ano do Veículo")
                placa = st.text_input("Placa do Veículo (ABC1234 / ABC1D23)").upper()
                servico = st.selectbox("Serviço Realizado", LISTA_SERVICOS)
            
            motivo = st.text_area("Diagnóstico e Observações")
            enviar = st.form_submit_button("Salvar Manutenção")
            
            if enviar:
                if placa and modelo and motivo:
                    with st.status("📦 Salvando dados na nuvem...", expanded=True) as status:
                        nova_linha = pd.DataFrame([[proxima_os, str(data), placa, f"{marca} {modelo}", propietario, servico, custo, motivo, responsavel]], 
                                                 columns=['OS', 'Data', 'Placa', 'Veículo', 'Proprietário', 'Serviço', 'Custo (R$)', 'Diagnóstico', 'Responsável'])
                        
                        df_final = pd.concat([df, nova_linha], ignore_index=True)
                        conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=df_final)
                        status.update(label="✅ Tudo pronto! Ordem salva.", state="complete", expanded=False)
                    
                    st.success(f"OS nº {proxima_os} registrada com sucesso!")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("⚠️ Campos obrigatórios: Placa, Modelo e Diagnóstico.")

    elif escolha == "Histórico e Financeiro":
        st.subheader("🔍 Consulta e Inteligência de Negócio")
        
        if df.empty or len(df.columns) < 2:
            st.info("Nenhum registro encontrado.")
        else:
            # --- DASHBOARD DE MÉTRICAS ---
            custos_numericos = pd.to_numeric(df['Custo (R$)'], errors='coerce').fillna(0)
            total_geral = custos_numericos.sum()
            ticket_medio = total_geral / len(df) if len(df) > 0 else 0
            servico_pop = df['Serviço'].mode()[0] if not df['Serviço'].empty else "N/A"

            m1, m2, m3 = st.columns(3)
            m1.metric("Faturamento Total", f"R$ {total_geral:,.2f}")
            m2.metric("Ticket Médio", f"R$ {ticket_medio:,.2f}")
            m3.metric("Serviço Frequente", servico_pop)
            
            st.write("---")
            
            # --- FILTROS ---
            c_filtro1, c_filtro2 = st.columns([2, 1])
            with c_filtro1:
                busca = st.text_input("Buscar por Placa ou OS:").upper()
            with c_filtro2:
                filtro_mec = st.selectbox("Filtrar por Mecânico", ["Todos"] + LISTA_MECANICOS)

            # Aplicando filtros
            df_filtrado = df.copy()
            if busca:
                df_filtrado = df_filtrado[(df_filtrado['Placa'].astype(str).str.contains(busca)) | (df_filtrado['OS'].astype(str).str.contains(busca))]
            if filtro_mec != "Todos":
                df_filtrado = df_filtrado[df_filtrado['Responsável'] == filtro_mec]

            # --- TABELA FORMATADA ---
            st.dataframe(
                df_filtrado.sort_values(by='OS', ascending=False),
                use_container_width=True,
                column_config={
                    "Custo (R$)": st.column_config.NumberColumn("Custo", format="R$ %.2f"),
                    "Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                    "OS": st.column_config.NumberColumn("OS", format="%d")
                },
                hide_index=True
            )

    elif escolha == "Sobre o APP":
        st.subheader("📱 Sobre o SGM Automotiva")
        st.markdown(f"""
        **Desenvolvedor:** Jonas Costa  
        **Versão:** 9.0 (Enterprise Edition)
        
        Este projeto foi concebido para automatizar o fluxo de trabalho de oficinas mecânicas. 
        Utiliza **Python**, **Streamlit** e integração em tempo real com **Google Sheets** para garantir que os dados estejam sempre acessíveis, seguros e fáceis de analisar.
        """)

    st.sidebar.markdown("---")
    st.sidebar.caption("SGM Automotiva v9.0")
