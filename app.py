import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="SGM Automotiva", layout="wide", page_icon="🚘")

# --- CONEXÃO COM GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    conn.reset()
    try:
        dados = conn.read(ttl=0)
        colunas_necessarias = ['OS', 'DATA', 'PLACA', 'MARCA', 'MODELO/ANO', 'PROPRIETÁRIO', 'SERVIÇO', 'CUSTO (R$)', 'PAGAMENTO (R$)', 'DIAGNÓSTICO', 'MECÂNICO']
        
        if dados is None or dados.empty:
            return pd.DataFrame(columns=colunas_necessarias)
        
        for col in colunas_necessarias:
            if col not in dados.columns:
                dados[col] = None
        return dados
    except:
        return pd.DataFrame(columns=['OS', 'DATA', 'PLACA', 'MARCA', 'MODELO/ANO', 'PROPRIETÁRIO', 'SERVIÇO', 'CUSTO (R$)', 'PAGAMENTO (R$)', 'DIAGNÓSTICO', 'MECÂNICO'])

# --- LISTAS DE OPÇÕES ---
LISTA_SERVICOS = [
    "ALINHAMENTO E BALANCEAMENTO", "AR-CONDICIONADO", "FREIOS", "LANTERNAGEM", "MOTOR", "REVISÃO GERAL", "SISTEMA ELÉTRICO", "SUSPENSÃO E AMORTECEDORES", "OUTROS DEFEITOS (ESPECIFICAR NO DIAGNÓSTICO)"
]

LISTA_MECANICOS = ["JONAS COSTA", "REBECA ALVES", "WILSON ALVES"]
LISTA_MARCA = [
    "AUDI", "BMW", "BYD", "CHEVROLET", "CITROËN", "FIAT", "FORD", "HONDA", "HYUNDAI", "INFINITI", "JAGUAR", "JEEP", "LEXUS", "MAZDA", "MERCEDES-BENZ", "MITSUBISHI", "NISSAN", "OUTROS", "RENAULT", "TOYOTA", "VOLKSWAGEN"
]

# --- SISTEMA DE LOGIN ---
def autenticacao():
    USUARIOS_PERMITIDOS = {
        "jonascosta": "MENGo2026@", "rebecaalves": "33091221", "wilsonalves": "RR2026", "oficina": "1234", "pedrobueno": "oficina1234", "davifraga": "oficina1234"
    }
    
    if "logado" not in st.session_state:
        st.session_state.logado = False

    if not st.session_state.logado:
        st.sidebar.markdown("# 🔐 Portal SGMa")
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
            c2.metric("Versão", "0.9.1b")
            c3.metric("Suporte", "Ativo")
            
        return False
    return True

# --- EXECUÇÃO DO SISTEMA ---
if autenticacao():
    st.sidebar.write(f"Logado como: **{st.session_state.usuario_nome}**")
    if st.sidebar.button("Sair / Logout"):
        st.session_state.logado = False
        st.rerun()

    menu = ["REGISTRAR O.S", "HISTÓRICO E FINANCEIRO", "SOBRE O APP"]
    escolha = st.sidebar.selectbox("Menu de Navegação:", menu)

    df = carregar_dados()

    if escolha == "REGISTRAR O.S":
        st.subheader("📝 REGISTRAR ORDEM DE SERVIÇO")
        
        if "lista_servicos_temp" not in st.session_state:
            st.session_state.lista_servicos_temp = []
            try:
                st.dataframe(df_temp[['SERVIÇO', 'CUSTO (RS)', DIAGNÓSTICO]], use_container_width=True)
            except:
                st.session_state.proxima_os = len(df) + 1
            
        st.info(f"📌 Ordem de Serviço atual: **{st.session_state.proxima_os}**")
        
        travado = len(st.session_state.lista_servicos_temp) > 0
        
        col1, col2 = st.columns(2)
        with col1:
            data_input = st.date_input("DATA", datetime.now(), disabled=travado)
            modelo_input = st.text_input("MODELO E ANO", disabled=travado, key="modelo")
            proprietario_input = st.text_input("PROPRIETÁRIO", disabled=travado, key="prop")
        with col2:
            marca_input = st.selectbox("MARCA", LISTA_MARCA, disabled=travado)
            placa_input = st.text_input("PLACA", disabled=travado, key="placa").upper()

        st.divider()

        st.markdown("### 🛠️ ADICIONAR SERVIÇO")
        c1, c2, c3, c4 = st.columns([4, 2, 2, 2])
        with c1:
            servico_item = st.selectbox("SERVIÇO REALIZADO", LISTA_SERVICOS)
        with c2:
            custo_item = st.number_input("CUSTO DO REPARO (R$)", min_value=0.0, step=10.0, format="%.2f")
        with c3:
            pagamento_item = st.number_input("PAGAMENTO RECEBIDO (R$)", min_value=0.0, step=10.0, format="%.2f")
        with c4:
            responsavel_os = st.selectbox("MECÂNICO RESPONSÁVEL", LISTA_MECANICOS)
        
        motivo_item = st.text_area("DIAGNÓSTICO E OBSERVAÇÕES", key="diag")

        if st.button("➕ ADICIONAR MAIS SERVIÇOS"):
            # A validação agora remove espaços e garante que o texto existe de fato
            if placa_input.strip() and modelo_input.strip() and motivo_item.strip():
                novo_item = {
                    'OS': st.session_state.proxima_os,
                    'DATA': str(data_input),
                    'PLACA': placa_input.strip(),
                    'MARCA': marca_input, 
                    'MODELO/ANO': modelo_input.strip(),
                    'PROPRIETÁRIO': proprietario_input.strip(),
                    'SERVIÇO': servico_item,
                    'CUSTO (R$)': custo_item,
                    'PAGAMENTO (R$)': pagamento_item,
                    'DIAGNÓSTICO': motivo_item.strip(),
                    'MECÂNICO': responsavel_os
                }
                st.session_state.lista_servicos_temp.append(novo_item)
                st.toast("Item adicionado com sucesso!")
                st.rerun()
            else:
                st.error("⚠️ Preencha os dados do veículo e o diagnóstico.")

        if st.session_state.lista_servicos_temp:
            st.markdown("---")
            st.markdown("### 📋 Resumo da OS")
            df_temp = pd.DataFrame(st.session_state.lista_servicos_temp)
            st.dataframe(df_temp[['SERVIÇO', 'CUSTO (R$)', 'PAGAMENTO (R$)', 'DIAGNÓSTICO']], use_container_width=True)
            
            st.write(f"**Total acumulado: R$ {df_temp['CUSTO (R$)'].sum():.2f}**")

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("💾 Finalizar e Salvar na Nuvem", type="primary", use_container_width=True):
                    with st.status("📦 Enviando para Google Sheets...", expanded=True) as status:
                        df_nuvem = carregar_dados()
                        df_final = pd.concat([df_nuvem, df_temp], ignore_index=True)
                        conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=df_final)
                        status.update(label="✅ OS Salva com Sucesso!", state="complete", expanded=False)
                    
                    st.session_state.lista_servicos_temp = [] 
                    st.balloons()
                    st.rerun()
            
            with col_btn2:
                if st.button("🗑️ Cancelar OS", use_container_width=True):
                    st.session_state.lista_servicos_temp = []
                    st.rerun()

    elif escolha == "HISTÓRICO E FINANCEIRO":
        st.subheader("🔍 CONSULTA E INTELIGÊNCIA DE NEGÓCIO")
        
        if df.empty or len(df.columns) < 2:
            st.info("NENHUM REGISTRO ENCONTRADO.")
        else:
            st.markdown("### 📅 Filtros de Busca")
            df['DATA_DT'] = pd.to_datetime(df['DATA'], errors='coerce')
            
            c_data1, c_data2, c_data3 = st.columns(3)
            with c_data1:
                filtro_dia = st.multiselect("Dia", options=sorted(df['DATA_DT'].dt.day.dropna().unique().astype(int)))
            with c_data2:
                filtro_mes = st.multiselect("Mês", options=sorted(df['DATA_DT'].dt.month.dropna().unique().astype(int)))
            with c_data3:
                filtro_ano = st.multiselect("Ano", options=sorted(df['DATA_DT'].dt.year.dropna().unique().astype(int)))

            c_busca1, c_busca2 = st.columns(2)
            with c_busca1:
                busca_placa_os = st.text_input("Buscar por Placa ou OS:").upper()
            with c_busca2:
                filtro_mec = st.selectbox("Filtrar por Mecânico", ["Todos"] + LISTA_MECANICOS)
            
            df_filtrado = df.copy()
            if filtro_dia: df_filtrado = df_filtrado[df_filtrado['DATA_DT'].dt.day.isin(filtro_dia)]
            if filtro_mes: df_filtrado = df_filtrado[df_filtrado['DATA_DT'].dt.month.isin(filtro_mes)]
            if filtro_ano: df_filtrado = df_filtrado[df_filtrado['DATA_DT'].dt.year.isin(filtro_ano)]
            if busca_placa_os:
                df_filtrado = df_filtrado[(df_filtrado['PLACA'].astype(str).str.contains(busca_placa_os)) | 
                                          (df_filtrado['OS'].astype(str).str.contains(busca_placa_os))]
            if filtro_mec != "Todos":
                df_filtrado = df_filtrado[df_filtrado['MECÂNICO'] == filtro_mec]

            st.write("---")
            custos_total = pd.to_numeric(df_filtrado['CUSTO (R$)'], errors='coerce').sum()
            pagamentos_total = pd.to_numeric(df_filtrado['PAGAMENTO (R$)'], errors='coerce').sum()
            saldo_liquido = pagamentos_total - custos_total

            m1, m2, m3 = st.columns(3)
            m1.metric("Faturamento (Entrada)", f"R$ {pagamentos_total:,.2f}")
            m2.metric("Custo de Reparo (Saída)", f"R$ {custos_total:,.2f}")
            st.metric("Saldo Líquido", f"R$ {saldo_liquido:,.2f}", delta=f"{saldo_liquido:,.2f}")
            
            st.write("---")
            st.dataframe(
                df_filtrado.drop(columns=['DATA_DT'], errors='ignore').sort_values(by='OS', ascending=False),
                use_container_width=True,
                column_config={
                    "CUSTO (R$)": st.column_config.NumberColumn("Custo", format="R$ %.2f"),
                    "PAGAMENTO (R$)": st.column_config.NumberColumn("Pagamento", format="R$ %.2f"),
                    "DATA": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                    "OS": st.column_config.NumberColumn("OS", format="%d")
                },
                hide_index=True
            )

    elif escolha == "SOBRE O APP":
        st.subheader("📱 SOBRE O SGM AUTOMOTIVA")
        st.markdown(f"""
        **DESENVOLVEDOR:** JONAS COSTA  
        **VERSÃO:** 0.9.1 (Beta Edition)  
        Este projeto foi concebido para automatizar o fluxo de trabalho de oficinas mecânicas.
        """)

    st.sidebar.markdown("---")
    st.sidebar.caption("SGM Automotiva v0.9.1 - BETA EDITION 🚀")
