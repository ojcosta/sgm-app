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
        colunas_necessarias = ['OS', 'DATA', 'PLACA', 'MARCA', 'MODELO/ANO', 'PROPIETÁRIO', 'SERVIÇO', 'CUSTO (R$)', 'DIAGNÓSTICO', 'MECÂNICO']
        
        if dados is None or dados.empty:
            return pd.DataFrame(columns=colunas_necessarias)
        
        for col in colunas_necessarias:
            if col not in dados.columns:
                dados[col] = None
        return dados
    except:
        return pd.DataFrame(columns=['OS', 'DATA', 'PLACA', 'MARCA', 'MODELO/ANO', 'PROPIETÁRIO', 'SERVIÇO', 'CUSTO (R$)', 'DIAGNÓSTICO', 'MECÂNICO'])

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
        "jonascosta": "MENGo2026@", "rebecaalves": "33091221", "wilsonalves": "RR2026", "oficina": "1234", "pedrobueno": "oficina1234", "davifraga": "oficina1234"
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
        
        if "lista_servicos_temp" not in st.session_state:
            st.session_state.lista_servicos_temp = []
            try:
                st.session_state.proxima_os = int(pd.to_numeric(df['OS'], errors='coerce').max() or 0) + 1
            except:
                st.session_state.proxima_os = len(df) + 1
            
        st.info(f"📌 Ordem de Serviço atual: **{st.session_state.proxima_os}**")
        
        travado = len(st.session_state.lista_servicos_temp) > 0
        
        col1, col2 = st.columns(2)
        with col1:
            data_form = st.date_input("Data do Serviço", datetime.now(), disabled=travado)
            modelo_form = st.text_input("Modelo e Ano do Veículo", disabled=travado)
            proprietario_form = st.text_input("Proprietário do Veículo", disabled=travado)
        with col2:
            marca_form = st.selectbox("Marca", LISTA_MARCA, disabled=travado)
            placa_form = st.text_input("Placa do Veículo (ABC1234 / ABC1D23)", disabled=travado).upper()

        st.divider()

        st.markdown("### 🛠️ Adicionar Serviço/Defeito")
        c1, c2, c3 = st.columns([3, 2, 1])
        with c1:
            servico_item = st.selectbox("Serviço Realizado", LISTA_SERVICOS)
        with c2:
            custo_item = st.number_input("Custo deste Item (R$)", min_value=0.0, step=10.0, format="%.2f")
        with c3:
            responsavel_os = st.selectbox("Mecânico Responsável", LISTA_MECANICOS)
        
        motivo_item = st.text_area("Diagnóstico e Observações deste item")

        if st.button("➕ Adicionar à mesma OS"):
            if placa_form and modelo_form and motivo_item:
                # CORREÇÃO: Alinhando nomes das chaves com as colunas da planilha
                novo_item = {
                    'OS': st.session_state.proxima_os,
                    'DATA': str(data_form),
                    'PLACA': placa_form,
                    'MARCA': marca_form, 
                    'MODELO/ANO': modelo_form,
                    'PROPIETÁRIO': proprietario_form,
                    'SERVIÇO': servico_item,
                    'CUSTO (R$)': custo_item,
                    'DIAGNÓSTICO': motivo_item,
                    'MECÂNICO': responsavel_os
                }
                st.session_state.lista_servicos_temp.append(novo_item)
                st.toast("Item adicionado!")
                st.rerun()
            else:
                st.error("⚠️ Preencha os dados do veículo e o diagnóstico.")

        if st.session_state.lista_servicos_temp:
            st.markdown("---")
            st.markdown("### 📋 Resumo da OS")
            df_temp = pd.DataFrame(st.session_state.lista_servicos_temp)
            st.dataframe(df_temp[['SERVIÇO', 'CUSTO (R$)', 'DIAGNÓSTICO']], use_container_width=True)
            
            st.write(f"**Total acumulado: R$ {df_temp['CUSTO (R$)'].sum():.2f}**")

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("💾 Finalizar e Salvar na Nuvem", type="primary", use_container_width=True):
                    with st.status("📦 Enviando para Google Sheets...", expanded=True) as status:
                        df_final = pd.concat([df, df_temp], ignore_index=True)
                        conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=df_final)
                        status.update(label="✅ OS Salva com Sucesso!", state="complete", expanded=False)
                    
                    st.session_state.lista_servicos_temp = [] 
                    st.balloons()
                    st.rerun()
            
            with col_btn2:
                if st.button("🗑️ Cancelar OS", use_container_width=True):
                    st.session_state.lista_servicos_temp = []
                    st.rerun()

    elif escolha == "Histórico e Financeiro":
        st.subheader("🔍 Consulta e Inteligência de Negócio")
        
        if df.empty or len(df.columns) < 2:
            st.info("Nenhum registro encontrado.")
        else:
            custos_numericos = pd.to_numeric(df['CUSTO (R$)'], errors='coerce').fillna(0)
            total_geral = custos_numericos.sum()
            ticket_medio = total_geral / len(df) if len(df) > 0 else 0
            servico_pop = df['SERVIÇO'].mode()[0] if not df['SERVIÇO'].empty else "N/A"

            m1, m2, m3 = st.columns(3)
            m1.metric("Faturamento Total", f"R$ {total_geral:,.2f}")
            m2.metric("Ticket Médio", f"R$ {ticket_medio:,.2f}")
            m3.metric("Serviço Frequente", servico_pop)
            
            st.write("---")
            
            busca = st.text_input("Buscar por Placa ou OS:").upper()
            filtro_mec = st.selectbox("Filtrar por Mecânico", ["Todos"] + LISTA_MECANICOS)

            df_filtrado = df.copy()
            if busca:
                df_filtrado = df_filtrado[(df_filtrado['PLACA'].astype(str).str.contains(busca)) | (df_filtrado['OS'].astype(str).str.contains(busca))]
            if filtro_mec != "Todos":
                df_filtrado = df_filtrado[df_filtrado['MECÂNICO'] == filtro_mec]

            st.dataframe(
                df_filtrado.sort_values(by='OS', ascending=False),
                use_container_width=True,
                column_config={
                    "CUSTO (R$)": st.column_config.NumberColumn("Custo", format="R$ %.2f"),
                    "DATA": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
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
        """)

    st.sidebar.markdown("---")
    st.sidebar.caption("SGM Automotiva v9.1")
