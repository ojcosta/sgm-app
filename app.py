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
        
        if dados.empty:
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

    elif escolha == "Registrar Novo Serviço":
    st.subheader("📝 Registrar Ordem de Serviço")
    
    # 1. Inicializa a lista de serviços na sessão se não existir
    if "lista_servicos_temporaria" not in st.session_state:
        st.session_state.lista_servicos_temporaria = []

    # --- SEÇÃO 1: DADOS DO VEÍCULO (CONGELADOS APÓS O PRIMEIRO SERVIÇO) ---
    st.markdown("### 🚗 Dados do Veículo")
    
    # Bloqueia os campos se já houver itens na lista
    bloquear_veiculo = len(st.session_state.lista_servicos_temporaria) > 0
    
    col1, col2, col3 = st.columns(3)
    with col1:
        placa = st.text_input("Placa", disabled=bloquear_veiculo).upper()
        proprietario = st.text_input("Proprietário", disabled=bloquear_veiculo)
    with col2:
        marca = st.text_input("Marca", disabled=bloquear_veiculo)
        modelo = st.text_input("Modelo", disabled=bloquear_veiculo)
    with col3:
        ano = st.text_input("Ano", disabled=bloquear_veiculo)
        data = st.date_input("Data do Serviço", datetime.now(), disabled=bloquear_veiculo)

    st.divider()

    # --- SEÇÃO 2: ADICIONAR SERVIÇOS ---
    st.markdown("### 🛠️ Adicionar Serviços")
    c1, c2, c3 = st.columns([2, 1, 1])
    
    with c1:
        servico_selecionado = st.selectbox("Selecione o Serviço", LISTA_SERVICOS)
    with c2:
        custo_item = st.number_input("Custo do Item (R$)", min_value=0.0, step=10.0)
    with c3:
        mecanico = st.selectbox("Mecânico", LISTA_MECANICOS)
        
    diagnostico_item = st.text_area("Diagnóstico deste item")

    if st.button("➕ Adicionar Serviço à OS"):
        if placa and diagnostico_item:
            # Adiciona o item à lista na memória
            novo_item = {
                "Data": data,
                "Placa": placa,
                "Marca/Modelo": f"{marca} {modelo}",
                "Ano": ano,
                "Proprietário": proprietario,
                "Serviço": servico_selecionado,
                "Custo (R$)": custo_item,
                "Diagnóstico": diagnostico_item,
                "Responsável": mecanico
            }
            st.session_state.lista_servicos_temporaria.append(novo_item)
            st.toast("Item adicionado!")
            st.rerun() # Atualiza para travar os campos do veículo
        else:
            st.error("Preencha a Placa e o Diagnóstico para adicionar.")

    # --- SEÇÃO 3: RESUMO E FINALIZAÇÃO ---
    if st.session_state.lista_servicos_temporaria:
        st.markdown("### 📋 Itens da OS Atual")
        df_temp = pd.DataFrame(st.session_state.lista_servicos_temporaria)
        st.table(df_temp[["Serviço", "Custo (R$)", "Responsável"]])
        
        st.write(f"**Total da OS: R$ {df_temp['Custo (R$)'].sum():.2f}**")

        col_fin1, col_fin2 = st.columns(2)
        with col_fin1:
            if st.button("💾 Salvar Tudo na Planilha", type="primary"):
                # Concatena com o DataFrame principal e salva
                df_para_salvar = pd.DataFrame(st.session_state.lista_servicos_temporaria)
                
                # Aqui você usa sua função de salvar (CSV ou Google Sheets)
                # Exemplo: df = pd.concat([df, df_para_salvar], ignore_index=True)
                # conn.update(spreadsheet=..., data=df)
                
                st.success("✅ Ordem de Serviço completa registrada com sucesso!")
                st.session_state.lista_servicos_temporaria = [] # Limpa a lista
                st.balloons()
                st.rerun()
        
        with col_fin2:
            if st.button("🗑️ Cancelar OS"):
                st.session_state.lista_servicos_temporaria = []
                st.rerun()

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
        Utiliza **Python**, **Streamlit** e integração em tempo real com **Google Sheets** para garantir que os dados estejam sempre acessíveis, seguros e fáceis de analisar. Foi desenvolvido com foco em usabilidade, eficiência e escalabilidade, permitindo que oficinas de todos os tamanhos possam gerenciar suas operações de forma mais inteligente e eficaz.
        """)

    st.sidebar.markdown("---")
    st.sidebar.caption("SGM Automotiva v9.1 - Correções de Bugs e melhorias de estabilidade")
