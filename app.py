import streamlit as st
import pandas as pd
from datetime import datetime, date

from streamlit_gsheets import GSheetsConnection

# ---------------------------------------------------------------------------
# CONFIGURAÇÕES INICIAIS
# ---------------------------------------------------------------------------
APP_VERSAO = "1.0.0"

st.set_page_config(page_title="SGMA", layout="wide", page_icon="🚘")

# ---------------------------------------------------------------------------
# CONEXÃO COM GOOGLE SHEETS
# ---------------------------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

COLUNAS = [
    'OS', 'DATA', 'MARCA', 'MODELO', 'KM ATUAL', 'PROPRIETÁRIO',
    'PLACA', 'ANO DE FABRICAÇÃO', 'CHASSI', 'SERVIÇO',
    'CUSTO (R$)', 'PAGAMENTO (R$)', 'MECÂNICO', 'DIAGNÓSTICO', 'STATUS'
]

def carregar_dados() -> pd.DataFrame:
    """Lê os dados do Google Sheets. Erros são exibidos ao usuário."""
    try:
        dados = conn.read(ttl=0)

        if dados is None or dados.empty:
            return pd.DataFrame(columns=COLUNAS)

        for col in COLUNAS:
            if col not in dados.columns:
                dados[col] = "FINALIZADO" if col == "STATUS" else None

        return dados[COLUNAS]

    except Exception as e:
        st.error(f"⚠️ Erro ao carregar dados do Google Sheets: {e}")
        return pd.DataFrame(columns=COLUNAS)

# ---------------------------------------------------------------------------
# LISTAS DE OPÇÕES
# ---------------------------------------------------------------------------
LISTA_SERVICOS = [
    "ALINHAMENTO E BALANCEAMENTO", "ARREFECIMENTO", "AR-CONDICIONADO",
    "BORRACHARIA", "CAIXA DE MARCHAS", "DIREÇÃO", "FREIOS",
    "LANTERNAGEM E CAPOTARIA", "MOTOR", "REVISÃO GERAL", "RODAS",
    "SISTEMA ELÉTRICO", "SISTEMA DE COMBUSTÍVEL", "SISTEMA DE ESCAPAMENTO",
    "SUSPENSÃO E AMORTECEDORES", "TRANSMISSÃO",
    "OUTROS DEFEITOS (ESPECIFICAR NO DIAGNÓSTICO)"
]

LISTA_MECANICOS = ["JONAS COSTA", "REBECA ALVES", "WILSON ALVES"]

LISTA_MARCA = [
    "AUDI", "BMW", "BYD", "CHEVROLET", "CITROËN", "FIAT", "FORD",
    "HONDA", "HYUNDAI", "INFINITI", "JAGUAR", "JEEP", "LEXUS", "MAZDA",
    "MERCEDES-BENZ", "MITSUBISHI", "NISSAN", "RENAULT", "TOYOTA",
    "VOLKSWAGEN", "OUTRO"
]

LISTA_STATUS = ["NA OFICINA", "EM ORÇAMENTO", "FINALIZADO"]

# ---------------------------------------------------------------------------
# PERFIS DE ACESSO
# Administradores: acesso total.
# Mecânicos: só veem as próprias OS e não acessam o financeiro completo.
# ---------------------------------------------------------------------------
PERFIS = {
    "admin":    ["jonascosta", "pedrobueno", "davifraga", "fabiomoraes", "wagnerandrade", "oficina"],
    "mecanico": ["rebecaalves", "wilsonalves"],
}

def perfil_do_usuario(usuario: str) -> str:
    for perfil, lista in PERFIS.items():
        if usuario in lista:
            return perfil
    return "mecanico"   # padrão mais restritivo

# ---------------------------------------------------------------------------
# SISTEMA DE LOGIN — senhas lidas de st.secrets (nunca no código-fonte)
# ---------------------------------------------------------------------------
# Exemplo de secrets.toml (Streamlit Cloud → Settings → Secrets):
#
# [usuarios]
# jonascosta    = "SuaSenhaAqui"
# rebecaalves   = "SuaSenhaAqui"
# ...

def autenticacao() -> bool:
    if "logado" not in st.session_state:
        st.session_state.logado = False

    if not st.session_state.logado:
        st.sidebar.markdown("# 🔐 PORTAL SGMA")
        usuario_input = st.sidebar.text_input("USUÁRIO").strip().lower()
        senha_input   = st.sidebar.text_input("SENHA", type="password")

        if st.sidebar.button("LOGIN", use_container_width=True):
            try:
                usuarios = st.secrets["usuarios"]
            except KeyError:
                st.sidebar.error("⚠️ Configuração de usuários ausente nos secrets.")
                return False

            if usuario_input in usuarios and usuarios[usuario_input] == senha_input:
                st.session_state.logado        = True
                st.session_state.usuario_nome  = usuario_input
                st.session_state.usuario_perfil = perfil_do_usuario(usuario_input)
                st.rerun()
            else:
                st.sidebar.error("⚠️ USUÁRIO OU SENHA INVÁLIDOS.")

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown("<h1 style='text-align:center;'>🚘 SGMA</h1>",        unsafe_allow_html=True)
            st.markdown("<h2 style='text-align:center;'>Sistema de Gestão Mecânica Automotiva</h2>", unsafe_allow_html=True)
            st.info("**UTILIZE SEU USUÁRIO E SENHA PARA ACESSAR.**")
            c1, c2, c3 = st.columns(3)
            c1.metric("STATUS",  "Online")
            c2.metric("VERSÃO",  APP_VERSAO)
            c3.metric("SUPORTE", "Ativo")
        return False

    return True


# ===========================================================================
# EXECUÇÃO PRINCIPAL
# ===========================================================================
if autenticacao():
    perfil = st.session_state.get("usuario_perfil", "mecanico")
    nome   = st.session_state.usuario_nome

    st.sidebar.write(f"Logado como: **{nome}**  \n`Perfil: {perfil}`")
    if st.sidebar.button("Logout"):
        st.session_state.logado = False
        st.rerun()

    # Menu adaptado ao perfil
    if perfil == "admin":
        menu = ["REGISTRAR O.S", "HISTÓRICO E FINANCEIRO", "SOBRE O APP"]
    else:
        menu = ["REGISTRAR O.S", "MINHAS ORDENS DE SERVIÇO", "SOBRE O APP"]

    escolha = st.sidebar.selectbox("MENU DE NAVEGAÇÃO:", menu)

    df = carregar_dados()

    # -----------------------------------------------------------------------
    # TELA: REGISTRAR O.S
    # -----------------------------------------------------------------------
    if escolha == "REGISTRAR O.S":
        st.subheader("📝 REGISTRAR ORDEM DE SERVIÇO")

        if "lista_servicos_temp" not in st.session_state:
            st.session_state.lista_servicos_temp = []

        # Número da próxima OS
        try:
            if not df.empty:
                ids_num = pd.to_numeric(df['OS'], errors='coerce').dropna()
                proxima_os = int(ids_num.max() + 1) if not ids_num.empty else 1
            else:
                proxima_os = 1
        except Exception:
            proxima_os = len(df) + 1

        st.info(f"📌 ORDEM DE SERVIÇO ATUAL: **{proxima_os}**")

        travado = len(st.session_state.lista_servicos_temp) > 0

        col1, col2 = st.columns(2)
        with col1:
            data_input        = st.date_input("DATA DO SERVIÇO", datetime.now(), disabled=travado)
            marca_input       = st.selectbox("MARCA", LISTA_MARCA, disabled=travado)
            modelo_input      = st.text_input("MODELO", disabled=travado, key="modelo")
            km_input          = st.number_input("KM ATUAL", min_value=0, step=1, format="%d", disabled=travado, key="km")
        with col2:
            proprietario_input = st.text_input("PROPRIETÁRIO", disabled=travado, key="prop")
            placa_input        = st.text_input("PLACA", disabled=travado, key="placa").upper()
            ano_input          = st.number_input("ANO DE FABRICAÇÃO", min_value=1900, max_value=datetime.now().year + 1, step=1, format="%d", disabled=travado, key="ano")
            chassi_input       = st.text_input("CHASSI", disabled=travado, key="chassi").upper()

        st.divider()
        st.markdown("### 🛠️ ADICIONAR SERVIÇO")

        c1, c2, c3, c4 = st.columns([4, 3, 2, 2])
        with c1:
            servico_item   = st.selectbox("SERVIÇO REALIZADO", LISTA_SERVICOS)
        with c2:
            custo_item     = st.number_input("CUSTO DO REPARO (R$)",   min_value=0.0, step=10.0, format="%.2f")
        with c3:
            pagamento_item = st.number_input("PAGAMENTO RECEBIDO (R$)", min_value=0.0, step=10.0, format="%.2f")
        with c4:
            responsavel_os = st.selectbox("MECÂNICO RESPONSÁVEL", LISTA_MECANICOS)

        status_item = st.selectbox("STATUS DO SERVIÇO", LISTA_STATUS)
        motivo_item = st.text_area("DIAGNÓSTICO E OBSERVAÇÕES", key="diag")

        # --- Botão ADICIONAR ---
        if st.button("➕ ADICIONAR MAIS SERVIÇOS"):
            erros = []
            if not placa_input.strip():   erros.append("Placa")
            if not modelo_input.strip():  erros.append("Modelo")
            if not motivo_item.strip():   erros.append("Diagnóstico")
            if custo_item == 0 and pagamento_item == 0:
                erros.append("Informe ao menos um valor financeiro (Custo ou Pagamento)")

            if erros:
                st.error(f"⚠️ Campos obrigatórios: {', '.join(erros)}.")
            else:
                st.session_state.lista_servicos_temp.append({
                    'OS':               proxima_os,
                    'DATA':             str(data_input),
                    'MARCA':            marca_input,
                    'MODELO':           modelo_input.strip(),
                    'KM ATUAL':         km_input,
                    'PROPRIETÁRIO':     proprietario_input.strip(),
                    'PLACA':            placa_input.strip(),
                    'ANO DE FABRICAÇÃO': ano_input,
                    'CHASSI':           chassi_input.strip(),
                    'SERVIÇO':          servico_item,
                    'CUSTO (R$)':       custo_item,
                    'PAGAMENTO (R$)':   pagamento_item,
                    'MECÂNICO':         responsavel_os,
                    'DIAGNÓSTICO':      motivo_item.strip(),
                    'STATUS':           status_item,
                })
                st.toast("✅ Serviço adicionado!")
                st.rerun()

        # --- Resumo da OS ---
        if st.session_state.lista_servicos_temp:
            st.markdown("---")
            st.markdown("### 📋 RESUMO DA OS")
            df_temp = pd.DataFrame(st.session_state.lista_servicos_temp)
            st.dataframe(
                df_temp[['SERVIÇO', 'CUSTO (R$)', 'PAGAMENTO (R$)', 'STATUS', 'DIAGNÓSTICO']],
                use_container_width=True
            )
            st.write(f"**TOTAL ACUMULADO: R$ {df_temp['CUSTO (R$)'].sum():.2f}**")

            col_btn1, col_btn2 = st.columns(2)

            with col_btn1:
                # Confirmação antes de salvar
                if st.button("💾 FINALIZAR E SALVAR NA NUVEM", type="primary", use_container_width=True):
                    st.session_state.confirmar_salvar = True

                if st.session_state.get("confirmar_salvar"):
                    st.warning("⚠️ Tem certeza que deseja salvar esta OS? Esta ação não pode ser desfeita.")
                    cc1, cc2 = st.columns(2)
                    with cc1:
                        if st.button("✅ SIM, SALVAR", use_container_width=True):
                            with st.status("📦 ENVIANDO PARA GOOGLE SHEETS...", expanded=True) as status:
                                try:
                                    df_nuvem = carregar_dados()
                                    df_final = pd.concat([df_nuvem, df_temp], ignore_index=True)
                                    conn.update(
                                        spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"],
                                        data=df_final
                                    )
                                    status.update(label="✅ OS SALVA COM SUCESSO!", state="complete", expanded=False)
                                    st.session_state.lista_servicos_temp = []
                                    st.session_state.confirmar_salvar    = False
                                    st.balloons()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Erro ao salvar: {e}")
                                    status.update(label="❌ Falha no envio.", state="error")
                    with cc2:
                        if st.button("❌ CANCELAR", use_container_width=True):
                            st.session_state.confirmar_salvar = False
                            st.rerun()

            with col_btn2:
                if st.button("🗑️ DESCARTAR OS", use_container_width=True):
                    st.session_state.lista_servicos_temp = []
                    st.session_state.pop("confirmar_salvar", None)
                    st.rerun()

    # -----------------------------------------------------------------------
    # TELA: HISTÓRICO E FINANCEIRO (admin) / MINHAS ORDENS (mecânico)
    # -----------------------------------------------------------------------
    elif escolha in ("HISTÓRICO E FINANCEIRO", "MINHAS ORDENS DE SERVIÇO"):
        if escolha == "HISTÓRICO E FINANCEIRO":
            st.subheader("🔍 CONSULTA E INTELIGÊNCIA DE NEGÓCIO")
        else:
            st.subheader(f"🔧 MINHAS ORDENS DE SERVIÇO — {nome.upper()}")

        if df.empty or len(df.columns) < 2:
            st.info("NENHUM REGISTRO ENCONTRADO.")
        else:
            # Mecânicos só veem as próprias OS
            if perfil == "mecanico":
                mecanico_nome = nome.replace(".", " ").upper()
                df = df[df['MECÂNICO'].str.upper() == mecanico_nome]

            df['DATA_DT'] = pd.to_datetime(df['DATA'], errors='coerce')

            st.markdown("### 📊 FILTROS DE BUSCA")

            # Intervalo de datas (substitui os 3 selects separados)
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                data_inicio = st.date_input("DATA INICIAL", value=date(2020, 1, 1))
            with col_d2:
                data_fim = st.date_input("DATA FINAL", value=date.today())

            c_busca1, c_busca2, c_busca3 = st.columns([2, 1, 1])
            with c_busca1:
                busca_placa_os = st.text_input("BUSCAR POR PLACA OU OS:").upper()
            with c_busca2:
                opcoes_mec = ["Todos"] + LISTA_MECANICOS if perfil == "admin" else [nome.upper()]
                filtro_mec = st.selectbox("FILTRAR POR MECÂNICO", opcoes_mec)
            with c_busca3:
                filtro_status = st.selectbox("FILTRAR POR STATUS", ["Todos"] + LISTA_STATUS)

            # Aplicar filtros
            df_f = df.copy()
            df_f = df_f[
                (df_f['DATA_DT'].dt.date >= data_inicio) &
                (df_f['DATA_DT'].dt.date <= data_fim)
            ]
            if busca_placa_os:
                df_f = df_f[
                    df_f['PLACA'].astype(str).str.contains(busca_placa_os) |
                    df_f['OS'].astype(str).str.contains(busca_placa_os)
                ]
            if filtro_mec != "Todos":
                df_f = df_f[df_f['MECÂNICO'] == filtro_mec]
            if filtro_status != "Todos":
                df_f = df_f[df_f['STATUS'] == filtro_status]

            st.write("---")

            # Métricas financeiras (admin vê tudo; mecânico vê só contagem)
            if perfil == "admin":
                custos_total    = pd.to_numeric(df_f['CUSTO (R$)'],    errors='coerce').sum()
                pagamentos_total = pd.to_numeric(df_f['PAGAMENTO (R$)'], errors='coerce').sum()
                saldo_liquido   = pagamentos_total - custos_total

                m1, m2, m3 = st.columns(3)
                m1.metric("FATURAMENTO (ENTRADA)", f"R$ {pagamentos_total:,.2f}")
                m2.metric("CUSTO DE REPARO (SAÍDA)", f"R$ {custos_total:,.2f}")
                m3.metric("SALDO LÍQUIDO", f"R$ {saldo_liquido:,.2f}", delta=f"{saldo_liquido:,.2f}")
            else:
                st.metric("TOTAL DE OS", len(df_f))

            st.write("---")

            colunas_exibir = COLUNAS if perfil == "admin" else [
                'OS', 'DATA', 'MARCA', 'MODELO', 'PLACA', 'SERVIÇO', 'STATUS', 'DIAGNÓSTICO'
            ]

            st.dataframe(
                df_f[[c for c in colunas_exibir if c in df_f.columns]]
                  .sort_values(by='OS', ascending=False),
                use_container_width=True,
                column_config={
                    "CUSTO (R$)":    st.column_config.NumberColumn("Custo",     format="R$ %.2f"),
                    "PAGAMENTO (R$)": st.column_config.NumberColumn("Pagamento", format="R$ %.2f"),
                    "DATA":          st.column_config.DateColumn("Data",        format="DD/MM/YYYY"),
                    "OS":            st.column_config.NumberColumn("OS",        format="%d"),
                },
                hide_index=True
            )

    # -----------------------------------------------------------------------
    # TELA: SOBRE
    # -----------------------------------------------------------------------
    elif escolha == "SOBRE O APP":
        st.subheader("📱 SOBRE O SGM AUTOMOTIVA")
        st.markdown(f"""
        **DESENVOLVEDOR:** JONAS COSTA  
        **VERSÃO:** {APP_VERSAO}

        O **SGMA** automatiza o fluxo de trabalho de oficinas mecânicas.

       Este projeto foi concebido para automatizar o fluxo de trabalho de oficinas mecânicas.

        Utiliza **Python**, **Streamlit** e integração em tempo real com **Google Sheets** para garantir que os dados estejam sempre acessíveis, seguros e fáceis de analisar. Foi desenvolvido com foco em usabilidade, eficiência e escalabilidade, permitindo que oficinas de todos os tamanhos possam gerenciar suas operações de forma mais inteligente e eficaz. O App é instável e necessita constatemente de atualizações, correções e melhorias. Agradecemos a compreensão e o feedback de todos os usuários para tornar o SGM Automotiva cada vez melhor!
        """)

    st.sidebar.markdown("---")
    st.sidebar.caption(f"SGM Automotiva v{APP_VERSAO} · BETA 🚀")
