import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="SGM AUTOMOTIVA", layout="wide", page_icon="🚘")

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
    "ALINHAMENTO E BALANCEAMENTO", "ARREFECIMENTO", "AR-CONDICIONADO", "BORRACHARIA", "CAIXA DE MARCHAS", "DIREÇÃO", "FREIOS", "LANTERNAGEM E CAPOTARIA", "MOTOR", "REVISÃO GERAL", "RODAS", "SISTEMA ELÉTRICO", "SISTEMA DE COMBUSTÍVEL", "SISTEMA DE ESCAPAMENTO", "SUSPENSÃO E AMORTECEDORES","TRANSMISSÃO", "OUTROS DEFEITOS (ESPECIFICAR NO DIAGNÓSTICO)"
]

LISTA_MECANICOS = ["JONAS COSTA", "REBECA ALVES", "WILSON ALVES"]
LISTA_MARCA = [
    "AUDI", "BMW", "BYD", "CHEVROLET", "CITROËN", "FIAT", "FORD", "HONDA", "HYUNDAI", "INFINITI", "JAGUAR", "JEEP", "LEXUS", "MAZDA", "MERCEDES-BENZ", "MITSUBISHI", "NISSAN", "RENAULT", "TOYOTA", "VOLKSWAGEN", "OUTROS"
]

# --- SISTEMA DE LOGIN ---
def autenticacao():
    USUARIOS_PERMITIDOS = {
        "jonascosta": "MENGo2026@", "rebecaalves": "33091221", "wilsonalves": "RR2026", "oficina": "1234", "pedrobueno": "oficina1234", "davifraga": "oficina1234", "fabiomoraes": "oficina1234","wagnerandrade": "oficina1234"
    }
    
    if "logado" not in st.session_state:
        st.session_state.logado = False

    if not st.session_state.logado:
        st.sidebar.markdown("# 🔐 PORTAL SGMa")
        usuario_input = st.sidebar.text_input("USUÁRIO")
        senha_input = st.sidebar.text_input("SENHA", type="password")
        
        if st.sidebar.button("LOGIN", use_container_width=True):
            if usuario_input in USUARIOS_PERMITIDOS and USUARIOS_PERMITIDOS[usuario_input] == senha_input:
                st.session_state.logado = True
                st.session_state.usuario_nome = usuario_input
                st.rerun()
            else:
                st.sidebar.error("⚠️ USUÁRIO OU SENHA INVÁLIDOS.")

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown("<h1 style='text-align: center;'>🚘 SGM Automotiva</h1>", unsafe_allow_html=True)
            st.info("**ACESSO RESTRITO.** USE O PAINEL LATERAL PARA ENTRAR.")
            
            c1, c2, c3 = st.columns(3)
            c1.metric("STATUS", "Online")
            c2.metric("VERSÃO", "0.9.1b")
            c3.metric("SUPORTE", "Ativo")
            
        return False
    return True

# --- EXECUÇÃO DO SISTEMA ---
if autenticacao():
    st.sidebar.write(f"Logado como: **{st.session_state.usuario_nome}**")
    if st.sidebar.button("Logout"):
        st.session_state.logado = False
        st.rerun()

    menu = ["REGISTRAR O.S", "HISTÓRICO E FINANCEIRO", "SOBRE O APP"]
    escolha = st.sidebar.selectbox("MENU DE NAVEGAÇÃO:", menu)

    df = carregar_dados()

    if escolha == "REGISTRAR O.S":
        st.subheader("📝 REGISTRAR ORDEM DE SERVIÇO")
        
        if "lista_servicos_temp" not in st.session_state:
            st.session_state.lista_servicos_temp = []
            
        # --- LÓGICA DE CONTAGEM REFORÇADA ---
        try:
            if not df.empty:
                # Converte para número, remove erros (NaN) e pega o maior
                ids_numericos = pd.to_numeric(df['OS'], errors='coerce').dropna()
                if not ids_numericos.empty:
                    ultima_os = ids_numericos.max()
                    st.session_state.proxima_os = int(ultima_os + 1)
                else:
                    st.session_state.proxima_os = 1
            else:
                st.session_state.proxima_os = 1
        except:
            st.session_state.proxima_os = len(df) + 1
            
        st.info(f"📌 ORDEM DE SERVIÇO ATUAL: **{st.session_state.proxima_os}**")
        
        travado = len(st.session_state.lista_servicos_temp) > 0
        
        col1, col2 = st.columns(2)
        with col1:
            data_input = st.date_input("DATA DO SERVIÇO", datetime.now(), disabled=travado)
            marca_input = st.selectbox("MARCA", LISTA_MARCA, disabled=travado)
            modelo_input = st.text_input("MODELO", disabled=travado, key="modelo")
            km_input = st.number_input("KM ATUAL", min_value=0, step=1, format="%d", disabled=travado, key="km")
        with col2:
            proprietario_input = st.text_input("PROPRIETÁRIO", disabled=travado, key="prop")
            placa_input = st.text_input("PLACA", disabled=travado, key="placa").upper()
            ano_input = st.number_input("ANO DE FABRICAÇÃO", min_value=0, step=1, format="%d", disabled=travado, key="ano")
            chassi_input = st.text_input("CHASSI", disabled=travado, key="chassi").upper()

        st.divider()

        st.markdown("### 🛠️ ADICIONAR SERVIÇO")
        c1, c2, c3, c4 = st.columns([4, 3, 2, 2])
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
                st.error("⚠️ PREENCHA OS DADOS DO VEÍCULO E O DIAGNÓSTICO.")

        if st.session_state.lista_servicos_temp:
            st.markdown("---")
            st.markdown("### 📋 RESUMO DA OS")
            df_temp = pd.DataFrame(st.session_state.lista_servicos_temp)
            st.dataframe(df_temp[['SERVIÇO', 'CUSTO (R$)', 'PAGAMENTO (R$)', 'DIAGNÓSTICO']], use_container_width=True)
            
            st.write(f"**TOTAL ACUMULADO: R$ {df_temp['CUSTO (R$)'].sum():.2f}**")

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("💾 FINALIZAR E SALVAR NA NUVEM", type="primary", use_container_width=True):
                    with st.status("📦 ENVIANDO PARA GOOGLE SHEETS...", expanded=True) as status:
                        df_nuvem = carregar_dados()
                        df_final = pd.concat([df_nuvem, df_temp], ignore_index=True)
                        conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=df_final)
                        status.update(label="✅ OS SALVA COM SUCESSO!", state="complete", expanded=False)
                    
                    st.session_state.lista_servicos_temp = [] 
                    st.balloons()
                    st.rerun()
            
            with col_btn2:
                if st.button("🗑️ CANCELAR OS", use_container_width=True):
                    st.session_state.lista_servicos_temp = []
                    st.rerun()

    elif escolha == "HISTÓRICO E FINANCEIRO":
        st.subheader("🔍 CONSULTA E INTELIGÊNCIA DE NEGÓCIO")
        
        if df.empty or len(df.columns) < 2:
            st.info("NENHUM REGISTRO ENCONTRADO.")
        else:
            st.markdown("### 📅 FILTROS DE BUSCA")
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
                busca_placa_os = st.text_input("BUSCAR POR PLACA OU OS:").upper()
            with c_busca2:
                filtro_mec = st.selectbox("FILTRAR POR MECÂNICO", ["Todos"] + LISTA_MECANICOS)
            
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
            m1.metric("FATURAMENTO (ENTRADA)", f"R$ {pagamentos_total:,.2f}")
            m2.metric("CUSTO DE REPARO (SAÍDA)", f"R$ {custos_total:,.2f}")
            m3.metric("SALDO LÍQUIDO", f"R$ {saldo_liquido:,.2f}", delta=f"{saldo_liquido:,.2f}")
            
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

        Utiliza **Python**, **Streamlit** e integração em tempo real com **Google Sheets** para garantir que os dados estejam sempre acessíveis, seguros e fáceis de analisar. Foi desenvolvido com foco em usabilidade, eficiência e escalabilidade, permitindo que oficinas de todos os tamanhos possam gerenciar suas operações de forma mais inteligente e eficaz. O App é instável e necessita constatemente de atualizações, correções e melhorias. Agradecemos a compreensão e o feedback de todos os usuários para tornar o SGM Automotiva cada vez melhor!
        """)

    st.sidebar.markdown("---")
    st.sidebar.caption("SGM Automotiva v0.9.1 - BETA EDITION 🚀")
