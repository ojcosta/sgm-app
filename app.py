import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="SGM Automotiva", layout="wide", page_icon="🚘")

# --- LINK DA LOGO (CORRIGIDO PARA LINK DIRETO) ---
URL_LOGO_SISTEMA = "https://i.imgur.com/3e7RIXC.png"

# --- CONEXÃO COM GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    try:
        dados = conn.read(ttl=0)
        # Padronização: remove espaços extras dos nomes das colunas
        dados.columns = [c.strip() for c in dados.columns]
        
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
        try:
            st.sidebar.image(URL_LOGO_SISTEMA, use_container_width=True)
        except:
            pass

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
            st.markdown("<br>", unsafe_allow_html=True)
            try:
                st.image(URL_LOGO_SISTEMA, width=200)
            except:
                pass
            st.markdown("<h1 style='text-align: center;'>SGM Automotiva</h1>", unsafe_allow_html=True)
            st.info("**Acesso Restrito.** Use o painel lateral para entrar.")
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Status", "Online")
            c2.metric("Versão", "9.2")
            c3.metric("Banco de Dados", "Conectado")
            
        return False
    return True

# --- EXECUÇÃO DO SISTEMA ---
if autenticacao():
    try:
        st.sidebar.image(URL_LOGO_SISTEMA, use_container_width=True)
    except:
        pass

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
                placa = st.text_input("Placa do Veículo").upper()
                servico = st.selectbox("Serviço Realizado", LISTA_SERVICOS)
            
            motivo = st.text_area("Diagnóstico e Observações")
            enviar = st.form_submit_button("Salvar Manutenção")
            
            if enviar:
                if placa and modelo and motivo:
                    with st.status("📦 Salvando dados...", expanded=True) as status:
                        nova_linha = pd.DataFrame([[proxima_os, str(data), placa, f"{marca} {modelo}", propietario, servico, custo, motivo, responsavel]], 
                                                 columns=['OS', 'Data', 'Placa', 'Veículo', 'Proprietário', 'Serviço', 'Custo (R$)', 'Diagnóstico', 'Responsável'])
                        
                        df_final = pd.concat([df, nova_linha], ignore_index=True)
                        conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=df_final)
                        status.update(label="✅ Salvo com sucesso!", state="complete", expanded=False)
                    
                    st.balloons()
                    st.rerun()
                else:
                    st.error("⚠️ Preencha os campos obrigatórios.")

    elif escolha == "Histórico e Financeiro":
        st.subheader("🔍 Consulta e Inteligência de Negócio")
        
        if df.empty:
            st.info("Nenhum registro encontrado.")
        else:
            # Identifica a coluna de custo mesmo se houver variação no nome
            col_custo = next((c for c in df.columns if 'Custo' in c), None)
            
            if col_custo:
                custos_numericos = pd.to_numeric(df[col_custo], errors='coerce').fillna(0)
                total_geral = custos_numericos.sum()
                ticket_medio = total_geral / len(df) if len(df) > 0 else 0
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Faturamento Total", f"R$ {total_geral:,.2f}")
                m2.metric("Ticket Médio", f"R$ {ticket_medio:,.2f}")
                
                if 'Serviço' in df.columns:
                    m3.metric("Serviço Frequente", df['Serviço'].mode()[0] if not df['Serviço'].empty else "N/A")
            
            st.write("---")
            
            c_filtro1, c_filtro2 = st.columns([2, 1])
            with c_filtro1:
                busca = st.text_input("Buscar por Placa ou OS:").upper()
            with c_filtro2:
                mecs = df['Responsável'].unique().tolist() if 'Responsável' in df.columns else []
                filtro_mec = st.selectbox("Filtrar por Mecânico", ["Todos"] + mecs)

            df_filtrado = df.copy()
            if busca:
                cols_busca = [c for c in ['Placa', 'OS'] if c in df_filtrado.columns]
                if cols_busca:
                    mask = df_filtrado[cols_busca].astype(str).apply(lambda x: x.str.contains(busca, case=False)).any(axis=1)
                    df_filtrado = df_filtrado[mask]

            if filtro_mec != "Todos" and 'Responsável' in df_filtrado.columns:
                df_filtrado = df_filtrado[df_filtrado['Responsável'] == filtro_mec]

            # Configuração visual da tabela
            config_cols = {
                "Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                "OS": st.column_config.NumberColumn("OS", format="%d")
            }
            if col_custo:
                config_cols[col_custo] = st.column_config.NumberColumn("Custo", format="R$ %.2f")

            st.dataframe(
                df_filtrado.sort_values(by=df_filtrado.columns[0], ascending=False),
                use_container_width=True,
                column_config=config_cols,
                hide_index=True
            )

    elif escolha == "Sobre o APP":
        st.subheader("📱 Sobre o SGM Automotiva")
        c_logo, c_texto = st.columns([1, 3])
        with c_logo:
            try: st.image(URL_LOGO_SISTEMA, use_container_width=True)
            except: pass
        with c_texto:
            st.markdown(f"""
            **Desenvolvedor:** Jonas Costa  
            **Versão:** 9.2 (Stable)
            
            Sistema desenvolvido para otimização de fluxos em oficinas mecânicas, integrando Python e Google Sheets.
            """)

    st.sidebar.markdown("---")
    st.sidebar.caption("SGM Automotiva v9.2")
