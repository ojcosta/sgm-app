import streamlit as st
import pandas as pd
from datetime import datetime, date

from streamlit_gsheets import GSheetsConnection
import hashlib

# ---------------------------------------------------------------------------
# UTILITÁRIOS DE SEGURANÇA
# ---------------------------------------------------------------------------
def _hash(s: str) -> str:
    """Retorna o SHA-256 da string. Nunca armazene senhas em texto puro."""
    return hashlib.sha256(s.encode()).hexdigest()

# ---------------------------------------------------------------------------
# CONFIGURAÇÕES INICIAIS
# ---------------------------------------------------------------------------
APP_VERSAO = "1.0.5"

st.set_page_config(page_title="SGMA", layout="wide", page_icon="🚘")

# ---------------------------------------------------------------------------
# CONEXÃO COM GOOGLE SHEETS
# ---------------------------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

COLUNAS = [
    'OS', 'DATA', 'MARCA', 'MODELO', 'KM ATUAL', 'PROPRIETÁRIO',
    'PLACA', 'ANO DE FABRICAÇÃO', 'CHASSI', 'SERVIÇO', 'DEFEITO',
    'DIAGNÓSTICO', 'SERVIÇO EXECUTADO',
    'CUSTO (R$)', 'PAGAMENTO (R$)', 'MECÂNICO', 'STATUS',
    'EDITADO_POR', 'DATA_EDICAO'
]

def carregar_dados() -> pd.DataFrame:
    """Lê os dados do Google Sheets. Erros são exibidos ao usuário."""
    try:
        dados = conn.read(ttl=0)

        if dados is None or dados.empty:
            return pd.DataFrame(columns=COLUNAS)

        for col in COLUNAS:
            if col not in dados.columns:
                if col == 'STATUS':
                    dados[col] = "FINALIZADO"
                elif col == 'DEFEITO':
                    dados[col] = "NÃO INFORMADO"
                elif col == 'SERVIÇO EXECUTADO':
                    dados[col] = "NÃO INFORMADO"
                elif col in ('EDITADO_POR', 'DATA_EDICAO'):
                    dados[col] = ""
                else:
                    dados[col] = None

        return dados[COLUNAS]

    except Exception as e:
        st.error(f"⚠️ Erro ao carregar dados do Google Sheets: {e}")
        return pd.DataFrame(columns=COLUNAS)


def calcular_proxima_os(dados: pd.DataFrame) -> int:
    """Calcula o número da próxima OS com base nos dados atuais."""
    try:
        if not dados.empty:
            ids_num = pd.to_numeric(dados['OS'], errors='coerce').dropna()
            return int(ids_num.max() + 1) if not ids_num.empty else 1
        return 1
    except Exception:
        return len(dados) + 1

# ---------------------------------------------------------------------------
# LISTAS DE OPÇÕES
# ---------------------------------------------------------------------------

# Dicionário: categoria → defeitos específicos
DEFEITOS_POR_SERVICO = {
    "ALINHAMENTO E BALANCEAMENTO": [
        "DESGASTE IRREGULAR DE PNEUS",
        "PUXANDO PARA DIREITA",
        "PUXANDO PARA ESQUERDA",
        "RUÍDO NAS RODAS AO ACELERAR",
        "VIBRAÇÃO NO VOLANTE",
        "VOLANTE TORTO",
        "OUTROS",
    ],
    "AR-CONDICIONADO": [
        "AR NÃO REFRIGERA",
        "BARULHO ESTRANHO",
        "CHEIRO RUIM NO AR-CONDICIONADO",
        "COMPRESSOR COM BARULHO",
        "CONDENSADOR DANIFICADO",
        "CONTROLADOR DO AR COM DEFEITO",
        "CORREIA DO COMPRESSOR ARREBENTADA",
        "EVAPORADOR COM VAZAMENTO",
        "FILTRO DE CABINE SUJO",
        "VAZAMENTO DE GÁS REFRIGERANTE",
        "OUTROS",
    ],
    "ARREFECIMENTO": [
        "MANGUEIRAS ARREBENTADAS",
        "MANGUEIRAS COM VAZAMENTO",
        "RADIADOR ENTUPIDO OU DANIFICADO",
        "RESERVATÓRIO DE EXPANSÃO RACHADO",
        "SUPERAQUECIMENTO DO MOTOR",
        "VAZAMENTO DE FLUIDO DE ARREFECIMENTO",
        "VENTOINHA NÃO FUNCIONA",
        "OUTROS",
    ],
    "BORRACHARIA E RODAS": [
        "PARAFUSO DE RODA COM DEFEITO",
        "PNEU CARECA / DESGASTADO",
        "PNEU DD FURADO",
        "PNEU DE FURADO",
        "PNEU TD FURADO",
        "PNEU TE FURADO",
        "RODA AMASSADA",
        "RODA TRAVADA",
        "ROLAMENTO DA RODA COM BARULHO",
        "TROCA DE PNEU",
        "VÁLVULA COM VAZAMENTO",
        "OUTROS DEFEITOS",
    ],
    "CAIXA DE MARCHAS": [
        "BARULHO ESTRANHO",
        "DIFICULDADE PARA ENGATAR MARCHA",
        "MARCHA ARRANHANDO",
        "MARCHA NÃO ENGRENA",
        "MARCHA SAINDO SOZINHA",
        "VAZAMENTO DE ÓLEO DA CAIXA",
        "OUTROS",
    ],
    "DIREÇÃO": [
        "BARULHO NA DIREÇÃO",
        "BOMBA DE DIREÇÃO DEFEITUOSA",
        "DIREÇÃO ELÉTRICA COM FALHA",
        "DIREÇÃO TRAVADA",
        "VAZAMENTO DE ÓLEO HIDRÁULICO",
        "VOLANTE COM FOLGA EXCESSIVA",
        "OUTROS",
    ],
    "EMBREAGEM": [
        "DISCO DE EMBREAGEM DESGASTADO",
        "EMBREAGEM COM BARULHO",
        "EMBREAGEM NÃO DESACOPLANDO",
        "EMBREAGEM PATINANDO",
        "PEDAL DURO",
        "PEDAL MOLE",
        "PLATO DE EMBREAGEM COM DEFEITO",
        "VIBRAÇÃO AO ACIONAR EMBREAGEM",
        "OUTROS",
    ],
    "FREIOS": [
        "CILINDRO MESTRE COM DEFEITO",
        "DISCO DE FREIO DESGASTADO",
        "FLUIDO DE FREIO BAIXO",
        "FREIO COM BARULHO (RANGENDO)",
        "FREIO DE MÃO NÃO SEGURA",
        "FREIO NÃO SEGURA",
        "FREIO PULSANDO",
        "PASTILHA DE FREIO GASTA",
        "PEDAL DE FREIO MOLE",
        "PUXANDO PARA DIREITA AO FREAR",
        "PUXANDO PARA ESQUERDA AO FREAR",
        "OUTROS",
    ],
    "LANTERNAGEM E CAPOTARIA": [
        "AMASSADO NA CARROCERIA",
        "ARGOLA DE REBOQUE AUSENTE / QUEBRADA",
        "ARRANHÃO NA PINTURA",
        "ASSENTO DO BANCO DANIFICADO",
        "ASSOALHO DANIFICADO",
        "BANCO DANIFICADO / QUEBRADO",
        "BORRACHA DA PORTA DANIFICADA",
        "BORRACHA DE VEDAÇÃO DANIFICADA",
        "CINTO DE SEGURANÇA COM DEFEITO",
        "ENCOSTO DO BANCO DANIFICADO",
        "FRISO AVARIADO",
        "LENTE DO RETROVISOR QUEBRADO",
        "PARA-CHOQUE AVARIADO",
        "PARABRISA TRINCADO/QUEBRADO",
        "PARA-SOL COM DEFEITO",
        "PEGA-MÃO QUEBRADO / AUSENTE",
        "PLACA SOLTA",
        "PINTURA DE CARROCERIA",
        "PORTA-LUVA COM DEFEITO",
        "PORTA DANIFICADA",
        "PORTA-MALA DANIFICADO",
        "RETROVISOR DANIFICADO",
        "VIDRO TRINCADO OU QUEBRADO",
        "OUTROS",
    ],
    "MOTOR": [
        "ALAVANCA DE ABERTURA DO CAPOT COM DEFEITO",
        "BARULHO NO MOTOR",
        "CONSUMO EXCESSIVO DE ÓLEO",
        "CORREIA ARREBENTADA",
        "CORREIA DESGASTADA",
        "FUMAÇA PRETA / BRANCA / AZUL",
        "LUZ DO MOTOR ACESA (CHECK ENGINE)",
        "MOTOR FALHANDO",
        "MOTOR NÃO LIGA",
        "PERDA DE POTÊNCIA",
        "TAMPA DO ÓLEO QUEBRADA",
        "VAZAMENTO DE ÓLEO DO MOTOR",
        "OUTROS",
    ],
    "REVISÃO GERAL": [
        "PRÉ-VIAGEM",
        "REVISÃO PROGRAMADA (KM)",
        "TROCA DE FILTRO DE AR",
        "TROCA DE ÓLEO E FILTRO",
        "TROCA DE VELAS DE IGNIÇÃO",
        "VERIFICAÇÃO GERAL DO VEÍCULO",
        "OUTROS",
    ],
    "SISTEMA DE COMBUSTÍVEL": [
        "BICO INJETOR COM FALHA",
        "BOMBA DE COMBUSTÍVEL COM DEFEITO",
        "CARBURADOR COM DEFEITO",
        "CONSUMO EXCESSIVO DE COMBUSTÍVEL",
        "FILTRO DE COMBUSTÍVEL ENTUPIDO",
        "PANE SECA",
        "TANQUE COM VAZAMENTO",
        "TAMPA DO TANQUE QUEBRADA",
        "OUTROS",
    ],
    "SISTEMA DE ESCAPAMENTO": [
        "CATALISADOR ENTUPIDO",
        "ESCAPAMENTO COM BARULHO / FURADO",
        "ESCAPAMENTO SOLTANDO FUMAÇA EXCESSIVA",
        "SONDA LAMBDA COM DEFEITO",
        "TUBO DE ESCAPAMENTO COM VAZAMENTO",
        "OUTROS",
    ],
    "SISTEMA ELÉTRICO": [
        "ALERTA COM DEFEITO",
        "ALTERNADOR COM DEFEITO",
        "BATERIA DESCARREGANDO",
        "CENTRAL ELETRÔNICA COM ERRO",
        "CHAVE DE IGNIÇÃO COM DEFEITO",
        "COMANDO DE SETAS",
        "ELEVADORES DE VIDROS COM DEFEITO",
        "FARÓIS COM DEFEITO",
        "FIAÇÃO COM DEFEITO",
        "FUSÍVEL QUEIMADO",
        "LIMPADOR DE PARABRISAS COM DEFEITO",
        "LANTERNAS COM DEFEITO",
        "LUZES COM DEFEITO",
        "MOTOR DE ARRANQUE COM DEFEITO",
        "NÃO VIRA",
        "PANE ELÉTRICA",
        "QUADRO DE BORDO COM DEFEITO",
        "RELES COM DEFEITO"
        "SENSOR COM FALHA",
        "SISTEMA DE ÁUDIO COM DEFEITO",
        "OUTROS",
    ],
    "SUSPENSÃO E AMORTECEDORES": [
        "AMORTECEDOR VAZANDO",
        "BARRA ESTABILIZADORA COM DEFEITO",
        "BIELETA DE SUSPENSÃO COM FOLGA",
        "BARULHO NA SUSPENSÃO (ESTALOS)",
        "CARRO BATENDO NO FUNDO",
        "MOLA QUEBRADA",
        "PIVÔ / BANDEJA COM DESGASTE",
        "OUTROS",
    ],
    "TRANSMISSÃO": [
        "BARULHO NA TRANSMISSÃO",
        "CÂMBIO AUTOMÁTICO COM FALHA",
        "PATINAÇÃO NA TRANSMISSÃO",
        "TRANSMISSÃO NÃO ENGATANDO",
        "TROCA DE ÓLEO DA TRANSMISSÃO",
        "OUTROS",
    ],
    "OUTROS DEFEITOS (ESPECIFICAR NO DIAGNÓSTICO)": [
        "ESPECIFICAR NO CAMPO DE DIAGNÓSTICO",
    ],
}
LISTA_SERVICOS = list(DEFEITOS_POR_SERVICO.keys())

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
    "admin":    ["jonascosta"],
    "mecanico": ["rebecaalves", "wilsonalves", "pedrobueno", "davifraga", "fabiomoraes", "wagnerandrade", "oficina"],
}

def perfil_do_usuario(usuario: str) -> str:
    for perfil, lista in PERFIS.items():
        if usuario in lista:
            return perfil
    return "mecanico"   # padrão mais restritivo

# Mapa username → nome real do mecânico (para filtro correto)
USUARIO_PARA_MECANICO = {
    "jonascosta":   "JONAS COSTA",
    "rebecaalves":  "REBECA ALVES",
    "wilsonalves":  "WILSON ALVES",
    "pedrobueno":   "PEDRO BUENO",
    "davifraga":    "DAVI FRAGA",
    "fabiomoraes":  "FABIO MORAES",
    "wagnerandrade":"WAGNER ANDRADE",
    "oficina":      "OFICINA",
}

def autenticacao() -> bool:
    if "logado" not in st.session_state:
        st.session_state.logado = False

    if not st.session_state.logado:

        # ── Sidebar: painel de login ────────────────────────────────────────
        st.sidebar.markdown(
            f"""
            <div style="display:flex;align-items:center;gap:10px;
                        padding-bottom:1rem;margin-bottom:1.25rem;
                        border-bottom:1px solid rgba(128,128,128,0.2);">
                <div style="width:36px;height:36px;border-radius:8px;
                            background:rgba(56,132,255,0.15);
                            display:flex;align-items:center;justify-content:center;
                            font-size:18px;">🔧</div>
                <div>
                    <div style="font-weight:600;font-size:15px;line-height:1.2;">SGMA</div>
                    <div style="font-size:11px;opacity:0.55;">Área restrita</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        usuario_input = st.sidebar.text_input("Usuário").strip().lower()
        senha_input   = st.sidebar.text_input("Senha", type="password")

        if st.sidebar.button("Entrar →", use_container_width=True, type="primary"):
            try:
                usuarios = st.secrets["usuarios"]
            except KeyError:
                st.sidebar.error("⚠️ Configuração de usuários ausente nos secrets.")
                return False

            if usuario_input in usuarios and usuarios[usuario_input] == _hash(senha_input):
                st.session_state.logado         = True
                st.session_state.usuario_nome   = usuario_input
                st.session_state.usuario_perfil = perfil_do_usuario(usuario_input)
                st.rerun()
            else:
                st.sidebar.error("Usuário ou senha inválidos.")

        st.sidebar.markdown(
            f"<div style='margin-top:auto;padding-top:2rem;"
            f"font-size:11px;opacity:0.4;text-align:center;'>"
            f"SGM Automotiva v{APP_VERSAO} · BETA</div>",
            unsafe_allow_html=True,
        )

        # ── Área principal: apresentação ────────────────────────────────────
        _, col_c, _ = st.columns([1, 2, 1])
        with col_c:
            st.markdown("<br>", unsafe_allow_html=True)

            st.markdown(
                """
                <div style="text-align:center;margin-bottom:1.5rem;">
                    <div style="width:72px;height:72px;border-radius:16px;
                                background:rgba(56,132,255,0.12);
                                display:flex;align-items:center;justify-content:center;
                                font-size:36px;margin:0 auto 1rem;">🚘</div>
                    <h1 style="margin:0 0 6px;font-size:26px;font-weight:600;">
                        Sistema de Gestão Mecânica Automotiva
                    </h1>
                    <p style="margin:0;font-size:15px;opacity:0.6;">
                        Ordens de serviço, histórico de veículos e controle financeiro
                        da sua oficina em um só lugar.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.info("Utilize seu usuário e senha na barra lateral para acessar.")

            c1, c2, c3 = st.columns(3)
            c1.metric("Status",  "✅ Online")
            c2.metric("Versão",  APP_VERSAO)
            c3.metric("Suporte", "✅ Ativo")

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
        menu = ["REGISTRAR O.S", "EDITAR O.S", "HISTÓRICO E FINANCEIRO", "SOBRE O APP"]
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

        # Número da próxima OS — estimativa para exibição
        # O número definitivo é recalculado no momento do salvamento
        proxima_os = calcular_proxima_os(df)
        st.info(f"📌 ORDEM DE SERVIÇO ESTIMADA: **{proxima_os}** *(confirmada ao salvar)*")

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
            ano_input          = st.number_input("ANO DE FABRICAÇÃO", min_value=1910, max_value=datetime.now().year + 1, step=1, format="%d", disabled=travado, key="ano")
            chassi_input       = st.text_input("CHASSI", disabled=travado, key="chassi").upper()

        st.divider()
        st.markdown("### 🛠️ ADICIONAR SERVIÇO")

        c1, c2, c3, c4 = st.columns([4, 3, 2, 2])
        with c1:
            servico_item   = st.selectbox("GRUPO DO SERVIÇO", LISTA_SERVICOS)
        with c2:
            custo_item     = st.number_input("CUSTO DO REPARO (R$)",   min_value=0.0, step=10.0, format="%.2f")
        with c3:
            pagamento_item = st.number_input("PAGAMENTO RECEBIDO (R$)", min_value=0.0, step=10.0, format="%.2f")
        with c4:
            responsavel_os = st.selectbox("MECÂNICO RESPONSÁVEL", LISTA_MECANICOS)

        # Defeito filtrado pela categoria
        defeitos_disponiveis = DEFEITOS_POR_SERVICO.get(servico_item, ["ESPECIFICAR NO CAMPO DE DIAGNÓSTICO"])
        defeito_item = st.selectbox("🔎 DEFEITO IDENTIFICADO", defeitos_disponiveis)

        st.markdown("---")
        col_diag1, col_diag2 = st.columns(2)
        with col_diag1:
            diagnostico_item = st.text_area(
                "🩺 DIAGNÓSTICO DO MECÂNICO",
                placeholder="DESCREVA O DEFEITO ENCONTRADO NO VEÍCULO.",
                key="diag",
                help="O que o mecânico identificou como causa do defeito."
            )
        with col_diag2:
            servico_executado_item = st.text_area(
                "🔧 SERVIÇO EXECUTADO",
                placeholder="DESCREVA O SERVIÇO EXECUTADO PELO MECÂNICO",
                key="exec",
                help="O que foi feito para solucionar o defeito."
            )

        # --- Botão ADICIONAR ---
        if st.button("➕ ADICIONAR MAIS SERVIÇOS"):
            erros = []
            if not placa_input.strip():              erros.append("Placa")
            if not modelo_input.strip():             erros.append("Modelo")
            if not diagnostico_item.strip():         erros.append("Diagnóstico do Mecânico")
            if not servico_executado_item.strip():   erros.append("Serviço Executado")
            if custo_item == 0 and pagamento_item == 0:
                erros.append("Informe ao menos um valor financeiro (Custo ou Pagamento)")

            if erros:
                st.error(f"⚠️ Campos obrigatórios: {', '.join(erros)}.")
            else:
                st.session_state.lista_servicos_temp.append({
                    'OS':                proxima_os,
                    'DATA':              str(data_input),
                    'MARCA':             marca_input,
                    'MODELO':            modelo_input.strip(),
                    'KM ATUAL':          km_input,
                    'PROPRIETÁRIO':      proprietario_input.strip(),
                    'PLACA':             placa_input.strip(),
                    'ANO DE FABRICAÇÃO': ano_input,
                    'CHASSI':            chassi_input.strip(),
                    'SERVIÇO':           servico_item,
                    'DEFEITO':           defeito_item,
                    'DIAGNÓSTICO':       diagnostico_item.strip(),
                    'SERVIÇO EXECUTADO': servico_executado_item.strip(),
                    'CUSTO (R$)':        custo_item,
                    'PAGAMENTO (R$)':    pagamento_item,
                    'MECÂNICO':          responsavel_os,
                    'STATUS':            "NA OFICINA",
                })
                st.toast("✅ Serviço adicionado!")
                st.rerun()

        # --- Resumo da OS ---
        if st.session_state.lista_servicos_temp:
            st.markdown("---")
            st.markdown("### 📋 RESUMO DA OS")
            df_temp = pd.DataFrame(st.session_state.lista_servicos_temp)
            st.dataframe(
                df_temp[['SERVIÇO', 'DEFEITO', 'DIAGNÓSTICO', 'SERVIÇO EXECUTADO', 'CUSTO (R$)', 'PAGAMENTO (R$)']],
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
                                    # Relê o Sheets agora para pegar o número de OS correto
                                    df_nuvem = carregar_dados()
                                    os_definitiva = calcular_proxima_os(df_nuvem)
                                    df_temp = pd.DataFrame(st.session_state.lista_servicos_temp)
                                    df_temp['OS'] = os_definitiva
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
    # TELA: EDITAR O.S (somente admin)
    # -----------------------------------------------------------------------
    elif escolha == "EDITAR O.S":
        st.subheader("✏️ EDITAR ORDEM DE SERVIÇO")

        if df.empty:
            st.info("NENHUM REGISTRO ENCONTRADO.")
        else:
            st.markdown("### 🔎 Localizar OS pelo número")
            num_os = st.number_input(
                "NÚMERO DA OS", min_value=1, step=1, format="%d",
                help="Digite o número exato da OS que deseja editar."
            )

            if st.button("🔍 BUSCAR OS", use_container_width=False):
                st.session_state.os_buscada = int(num_os)
                st.session_state.pop("confirmar_edicao", None)

            os_buscada = st.session_state.get("os_buscada")

            if os_buscada:
                linhas = df[pd.to_numeric(df['OS'], errors='coerce') == os_buscada]

                if linhas.empty:
                    st.error(f"⚠️ OS nº {os_buscada} não encontrada.")
                else:
                    # Se a OS tiver mais de uma linha (múltiplos serviços),
                    # exibe todas e o admin escolhe qual linha editar
                    if len(linhas) > 1:
                        st.info(f"A OS {os_buscada} possui **{len(linhas)} linhas** (múltiplos serviços). Selecione qual deseja editar:")
                        idx_escolhido = st.selectbox(
                            "LINHA DA OS",
                            options=linhas.index.tolist(),
                            format_func=lambda i: f"Serviço: {linhas.loc[i, 'SERVIÇO']} | Defeito: {linhas.loc[i, 'DEFEITO']} | Mecânico: {linhas.loc[i, 'MECÂNICO']}"
                        )
                    else:
                        idx_escolhido = linhas.index[0]

                    row = df.loc[idx_escolhido]

                    st.markdown(f"---\n### 📋 Editando OS **{os_buscada}**")

                    # Última edição (auditoria)
                    if pd.notna(row.get('EDITADO_POR')) and str(row.get('EDITADO_POR', '')).strip():
                        st.caption(f"📝 Última edição por **{row['EDITADO_POR']}** em {row['DATA_EDICAO']}")

                    col1, col2 = st.columns(2)
                    with col1:
                        # DATA
                        try:
                            data_val = pd.to_datetime(row['DATA']).date()
                        except Exception:
                            data_val = date.today()
                        e_data = st.date_input("DATA DO SERVIÇO", value=data_val, key="e_data")

                        # MARCA
                        marca_idx = LISTA_MARCA.index(row['MARCA']) if row['MARCA'] in LISTA_MARCA else len(LISTA_MARCA) - 1
                        e_marca = st.selectbox("MARCA", LISTA_MARCA, index=marca_idx, key="e_marca")

                        e_modelo = st.text_input("MODELO", value=str(row['MODELO']), key="e_modelo")
                        e_km     = st.number_input("KM ATUAL", min_value=0, step=1,
                                                   value=int(pd.to_numeric(row['KM ATUAL'], errors='coerce') or 0),
                                                   format="%d", key="e_km")
                    with col2:
                        e_prop   = st.text_input("PROPRIETÁRIO", value=str(row['PROPRIETÁRIO']), key="e_prop")
                        e_placa  = st.text_input("PLACA", value=str(row['PLACA']), key="e_placa").upper()
                        e_ano    = st.number_input("ANO DE FABRICAÇÃO", min_value=1910,
                                                   max_value=datetime.now().year + 1, step=1,
                                                   value=int(pd.to_numeric(row['ANO DE FABRICAÇÃO'], errors='coerce') or 2000),
                                                   format="%d", key="e_ano")
                        e_chassi = st.text_input("CHASSI", value=str(row['CHASSI']), key="e_chassi").upper()

                    st.divider()
                    c1, c2, c3, c4 = st.columns([4, 3, 2, 2])
                    with c1:
                        serv_idx = LISTA_SERVICOS.index(row['SERVIÇO']) if row['SERVIÇO'] in LISTA_SERVICOS else 0
                        e_servico = st.selectbox("GRUPO DO SERVIÇO", LISTA_SERVICOS, index=serv_idx, key="e_servico")
                    with c2:
                        e_custo = st.number_input("CUSTO DO REPARO (R$)", min_value=0.0, step=10.0, format="%.2f",
                                                  value=float(pd.to_numeric(row['CUSTO (R$)'], errors='coerce') or 0.0),
                                                  key="e_custo")
                    with c3:
                        e_pgto  = st.number_input("PAGAMENTO RECEBIDO (R$)", min_value=0.0, step=10.0, format="%.2f",
                                                  value=float(pd.to_numeric(row['PAGAMENTO (R$)'], errors='coerce') or 0.0),
                                                  key="e_pgto")
                    with c4:
                        mec_idx = LISTA_MECANICOS.index(row['MECÂNICO']) if row['MECÂNICO'] in LISTA_MECANICOS else 0
                        e_mec   = st.selectbox("MECÂNICO RESPONSÁVEL", LISTA_MECANICOS, index=mec_idx, key="e_mec")

                    # Defeito filtrado pelo serviço escolhido
                    defeitos_ed = DEFEITOS_POR_SERVICO.get(e_servico, ["ESPECIFICAR NO CAMPO DE DIAGNÓSTICO"])
                    def_idx = defeitos_ed.index(row['DEFEITO']) if row['DEFEITO'] in defeitos_ed else 0
                    e_defeito = st.selectbox("🔎 DEFEITO IDENTIFICADO", defeitos_ed, index=def_idx, key="e_defeito")

                    status_idx = LISTA_STATUS.index(row['STATUS']) if row['STATUS'] in LISTA_STATUS else 0
                    e_status = st.selectbox("STATUS DO SERVIÇO", LISTA_STATUS, index=status_idx, key="e_status")

                    st.markdown("---")
                    col_d1, col_d2 = st.columns(2)
                    with col_d1:
                        e_diag = st.text_area("🩺 DIAGNÓSTICO DO MECÂNICO", value=str(row['DIAGNÓSTICO']), key="e_diag")
                    with col_d2:
                        e_exec = st.text_area("🔧 SERVIÇO EXECUTADO", value=str(row['SERVIÇO EXECUTADO']), key="e_exec")

                    st.markdown("---")
                    if st.button("💾 SALVAR ALTERAÇÕES", type="primary", use_container_width=True):
                        erros_ed = []
                        if not e_placa.strip():   erros_ed.append("Placa")
                        if not e_modelo.strip():  erros_ed.append("Modelo")
                        if not e_diag.strip():    erros_ed.append("Diagnóstico")
                        if not e_exec.strip():    erros_ed.append("Serviço Executado")

                        if erros_ed:
                            st.error(f"⚠️ Campos obrigatórios: {', '.join(erros_ed)}.")
                        else:
                            st.session_state.confirmar_edicao = True

                    if st.session_state.get("confirmar_edicao"):
                        st.warning("⚠️ Confirma a alteração desta OS? A linha será sobrescrita no Google Sheets.")
                        cc1, cc2 = st.columns(2)
                        with cc1:
                            if st.button("✅ SIM, ALTERAR", use_container_width=True, key="btn_sim_edit"):
                                with st.status("📦 ATUALIZANDO NO GOOGLE SHEETS...", expanded=True) as s_edit:
                                    try:
                                        df_nuvem = carregar_dados()
                                        agora    = datetime.now().strftime("%d/%m/%Y %H:%M")

                                        df_nuvem.loc[idx_escolhido, 'DATA']              = str(e_data)
                                        df_nuvem.loc[idx_escolhido, 'MARCA']             = e_marca
                                        df_nuvem.loc[idx_escolhido, 'MODELO']            = e_modelo.strip()
                                        df_nuvem.loc[idx_escolhido, 'KM ATUAL']          = e_km
                                        df_nuvem.loc[idx_escolhido, 'PROPRIETÁRIO']      = e_prop.strip()
                                        df_nuvem.loc[idx_escolhido, 'PLACA']             = e_placa.strip()
                                        df_nuvem.loc[idx_escolhido, 'ANO DE FABRICAÇÃO'] = e_ano
                                        df_nuvem.loc[idx_escolhido, 'CHASSI']            = e_chassi.strip()
                                        df_nuvem.loc[idx_escolhido, 'SERVIÇO']           = e_servico
                                        df_nuvem.loc[idx_escolhido, 'DEFEITO']           = e_defeito
                                        df_nuvem.loc[idx_escolhido, 'DIAGNÓSTICO']       = e_diag.strip()
                                        df_nuvem.loc[idx_escolhido, 'SERVIÇO EXECUTADO'] = e_exec.strip()
                                        df_nuvem.loc[idx_escolhido, 'CUSTO (R$)']        = e_custo
                                        df_nuvem.loc[idx_escolhido, 'PAGAMENTO (R$)']    = e_pgto
                                        df_nuvem.loc[idx_escolhido, 'MECÂNICO']          = e_mec
                                        df_nuvem.loc[idx_escolhido, 'STATUS']            = e_status
                                        df_nuvem.loc[idx_escolhido, 'EDITADO_POR']       = nome
                                        df_nuvem.loc[idx_escolhido, 'DATA_EDICAO']       = agora

                                        conn.update(
                                            spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"],
                                            data=df_nuvem
                                        )
                                        s_edit.update(label="✅ OS ATUALIZADA COM SUCESSO!", state="complete", expanded=False)
                                        st.session_state.pop("os_buscada", None)
                                        st.session_state.pop("confirmar_edicao", None)
                                        st.balloons()
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Erro ao atualizar: {e}")
                                        s_edit.update(label="❌ Falha na atualização.", state="error")
                        with cc2:
                            if st.button("❌ CANCELAR", use_container_width=True, key="btn_cancel_edit"):
                                st.session_state.pop("confirmar_edicao", None)
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
                mecanico_nome = USUARIO_PARA_MECANICO.get(nome, nome.upper())
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
                'OS', 'DATA', 'MARCA', 'MODELO', 'PLACA', 'SERVIÇO',
                'DEFEITO', 'DIAGNÓSTICO', 'SERVIÇO EXECUTADO', 'STATUS'
            ]

            st.dataframe(
                df_f[[c for c in colunas_exibir if c in df_f.columns]]
                  .assign(OS=lambda x: pd.to_numeric(x['OS'], errors='coerce'))
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
        st.subheader("📱 Sobre o SGMA")
        st.markdown(f"""
        **Desenvolvedor:** Jonas Costa  
        **Versão:** {APP_VERSAO}

        O **SGMA** centraliza o registro de ordens de serviço, controle financeiro e histórico de atendimentos da sua oficina em um único lugar.

        Utiliza **Python**, **Streamlit** e integração em tempo real com **Google Sheets** para garantir dados sempre acessíveis, seguros e fáceis de analisar. Desenvolvido com foco em usabilidade, eficiência e escalabilidade — em constante evolução.

        Sugestões e críticas: [WhatsApp](https://wa.me/5521987360343) 📞
        """)

    st.sidebar.markdown("---")
    st.sidebar.caption(f"SGM Automotiva v{APP_VERSAO} · BETA 🚀")
