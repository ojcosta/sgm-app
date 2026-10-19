import re
import streamlit as st
import pandas as pd
import gspread
import altair as alt
from datetime import datetime, date
from zoneinfo import ZoneInfo

# O servidor do Streamlit Cloud roda em UTC (3h à frente de Brasília). datetime.now()/date.today() dariam
# hora errada e, depois das 21h, a data do dia seguinte. Use SEMPRE agora()/hoje().
FUSO = ZoneInfo("America/Sao_Paulo")


def agora() -> datetime:
    """Data e hora atuais de Brasília (sem tzinfo, para comparar com datas lidas da planilha)."""
    return datetime.now(FUSO).replace(tzinfo=None)


def hoje() -> date:
    return agora().date()

# ⚠️ Antes de alterar a aba "CADASTROS" (nome, colunas, valores de STATUS),
# leia SCHEMA.md — essa estrutura é compartilhada com o repositório
# sgmaforms, sem checagem automática entre os dois.

from streamlit_gsheets import GSheetsConnection
import bcrypt
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# ---------------------------------------------------------------------------
# UTILITÁRIOS DE SEGURANÇA
# ---------------------------------------------------------------------------
def _verificar_senha(senha_digitada: str, hash_armazenado: str) -> tuple[bool, str]:
    """
    Verifica senha contra hash bcrypt armazenado no secrets.toml.
    Para gerar o hash de uma nova senha, rode no terminal:
        import bcrypt
        print(bcrypt.hashpw("sua_senha".encode(), bcrypt.gensalt()).decode())
    Cole o resultado no secrets.toml no lugar da senha.

    Retorna (sucesso, motivo_tecnico). O motivo_tecnico é só para debug —
    NUNCA deve ser exibido a usuários finais em produção.
    """
    if not hash_armazenado:
        return False, "HASH_VAZIO"

    hash_armazenado = hash_armazenado.strip()  # remove espaço/quebra de linha colados sem querer

    if not hash_armazenado.startswith(("$2a$", "$2b$", "$2y$")):
        return False, "HASH_ARMAZENADO_NAO_E_BCRYPT"

    try:
        ok = bcrypt.checkpw(senha_digitada.encode(), hash_armazenado.encode())
        return ok, ("SENHA_CORRETA" if ok else "SENHA_INCORRETA")
    except Exception as e:
        return False, f"ERRO_VERIFICACAO: {type(e).__name__}"

# ---------------------------------------------------------------------------
# CONFIGURAÇÕES INICIAIS
# ---------------------------------------------------------------------------
APP_VERSAO = "0.9.5b"

st.set_page_config(page_title="SGMA", layout="wide", page_icon="🚘")

# ---------------------------------------------------------------------------
# CONEXÃO COM GOOGLE SHEETS
# ---------------------------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

COLUNAS = [
    'OS', 'DATA', 'MARCA', 'MODELO', 'KM ATUAL', 'PROPRIETÁRIO',
    'PLACA', 'ANO DE FABRICAÇÃO', 'CHASSI', 'SERVIÇO', 'DEFEITO',
    'DIAGNÓSTICO', 'SERVIÇO EXECUTADO',
    'CUSTO (R$)', 'PAGAMENTO (R$)', 'MECÂNICO',
    'EDITADO_POR', 'DATA_EDICAO'
]

WORKSHEET_SOLICITACOES = "CADASTROS"
WORKSHEET_SEQUENCIA    = "SEQUENCIA"   # aba auxiliar: reserva de números de OS (ver reservar_numero_os)

class FalhaLeituraSheets(Exception):
    """A leitura da planilha falhou. Em caminhos de ESCRITA isto deve abortar a operação."""


def _normalizar_colunas(dados: pd.DataFrame) -> pd.DataFrame:
    for col in COLUNAS:
        if col not in dados.columns:
            if col in ('DEFEITO', 'SERVIÇO EXECUTADO'):
                dados[col] = "NÃO INFORMADO"
            elif col in ('EDITADO_POR', 'DATA_EDICAO'):
                dados[col] = ""
            else:
                dados[col] = None
    return dados[COLUNAS]


def carregar_dados_estrito() -> pd.DataFrame:
    """
    Para caminhos de ESCRITA. Se a leitura falhar, levanta FalhaLeituraSheets
    em vez de devolver um DataFrame vazio — um vazio "de mentira" seguido de
    conn.update() sobrescreve a planilha inteira e apaga o histórico.
    """
    try:
        dados = conn.read(ttl=0)
    except Exception as e:
        raise FalhaLeituraSheets(f"Falha ao ler a planilha: {e}") from e

    if dados is None:
        raise FalhaLeituraSheets("A leitura da planilha retornou None.")
    if dados.empty:
        return pd.DataFrame(columns=COLUNAS)
    return _normalizar_colunas(dados)


def carregar_dados() -> pd.DataFrame:
    """Para EXIBIÇÃO. Erros são mostrados ao usuário. Nunca use o resultado para gravar."""
    try:
        return carregar_dados_estrito()
    except FalhaLeituraSheets as e:
        st.error(f"⚠️ Erro ao carregar dados do Google Sheets: {e}")
        return pd.DataFrame(columns=COLUNAS)


def exigir_planilha_nao_encolheu(df_atual: pd.DataFrame, df_visto: pd.DataFrame) -> None:
    """Defesa extra antes de qualquer conn.update(): nunca gravar menos linhas do que o usuário viu."""
    if len(df_atual) < len(df_visto):
        raise FalhaLeituraSheets(
            f"A planilha tem {len(df_atual)} linha(s) agora, mas {len(df_visto)} foram "
            f"exibidas nesta sessão. Gravação abortada para evitar perda de dados."
        )


def carregar_solicitacoes() -> pd.DataFrame:
    """Lê a aba de solicitações de clientes (formulário público)."""
    try:
        dados = conn.read(worksheet=WORKSHEET_SOLICITACOES, ttl=0)
        if dados is None or dados.empty:
            return pd.DataFrame(columns=["NOME", "TELEFONE", "PLACA", "DEFEITO RELATADO", "DATA DA SOLICITAÇÃO", "STATUS"])
        return dados
    except Exception as e:
        st.error(f"⚠️ Erro ao carregar solicitações: {e}")
        return pd.DataFrame(columns=["NOME", "TELEFONE", "PLACA", "DEFEITO RELATADO", "DATA DA SOLICITAÇÃO", "STATUS"])


def estimar_proxima_os(dados: pd.DataFrame) -> int:
    """
    SÓ PARA EXIBIÇÃO. O número definitivo vem de reservar_numero_os().
    Pode divergir do definitivo (outro usuário reservando, buracos na sequência).
    """
    if dados.empty:
        return 1
    ids_num = pd.to_numeric(dados['OS'], errors='coerce').dropna()
    return int(ids_num.max() + 1) if not ids_num.empty else 1


# ---------------------------------------------------------------------------
# GRAVAÇÃO SEGURA DE NOVAS OS (append + número reservado)
# ---------------------------------------------------------------------------
class ErroGravacaoOS(Exception):
    """Falha ao reservar número ou anexar a OS. Nada foi sobrescrito."""


@st.cache_resource(show_spinner=False)
def _planilha_gspread():
    """Planilha aberta com gspread, usando as MESMAS credenciais do st.connection."""
    cfg = dict(st.secrets["connections"]["gsheets"])
    url = cfg.pop("spreadsheet")
    cfg.pop("worksheet", None)
    return gspread.service_account_from_dict(cfg).open_by_url(url)


def _linha_do_append(resposta: dict) -> int:
    """Extrai o nº da linha onde o Sheets gravou o append (ex.: "'SEQUENCIA'!A5:C5" -> 5)."""
    try:
        faixa = resposta["updates"]["updatedRange"]
        return int(re.search(r"!\$?[A-Z]+(\d+)", faixa).group(1))
    except Exception as e:
        raise ErroGravacaoOS(f"Resposta inesperada do Google Sheets no append: {resposta!r}") from e


def _valor_celula(v):
    """Converte para tipos simples; None/NaN viram vazio."""
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except (TypeError, ValueError):
        pass
    if hasattr(v, "item"):          # tipos numpy -> Python
        v = v.item()
    return v


def reservar_numero_os(usuario: str) -> int:
    """
    Número de OS único, sem corrida: cada reserva é um APPEND na aba SEQUENCIA e o
    Google Sheets devolve a linha atribuída — que é distinta para cada chamada.
        A1 = cabeçalho | A2 = semente (último nº de OS já usado) | linha N>=3 = reserva
        nº da OS = semente + (N - 2)
    Efeito colateral aceito: se o salvamento falhar depois da reserva, o número fica
    "queimado" (buraco na sequência).
    """
    try:
        ws = _planilha_gspread().worksheet(WORKSHEET_SEQUENCIA)
    except gspread.WorksheetNotFound as e:
        raise ErroGravacaoOS(
            f"Aba '{WORKSHEET_SEQUENCIA}' não existe na planilha. Crie-a: A1='OS', "
            f"B1='RESERVADO_EM', C1='RESERVADO_POR' e, em A2, o último nº de OS já usado."
        ) from e

    bruto = ws.acell("A2").value
    try:
        semente = int(float(str(bruto).strip().replace(",", ".")))
    except (TypeError, ValueError) as e:
        raise ErroGravacaoOS(f"Semente inválida em {WORKSHEET_SEQUENCIA}!A2: {bruto!r}") from e

    carimbo = agora().strftime("%d/%m/%Y %H:%M:%S")
    resposta = ws.append_rows([["", carimbo, usuario]], value_input_option="RAW", table_range="A1")
    linha = _linha_do_append(resposta)
    if linha < 3:
        raise ErroGravacaoOS(f"Reserva gravada em linha inesperada ({linha}) — verifique a aba {WORKSHEET_SEQUENCIA}.")

    os_num = semente + (linha - 2)
    try:  # auditoria (best effort): escreve o nº na linha reservada
        ws.update_cell(linha, 1, os_num)
    except Exception:
        pass
    return os_num


def _qtd_linhas_da_os(ws, col_os: int, os_num: int) -> int:
    n = 0
    for v in ws.col_values(col_os)[1:]:
        try:
            if int(float(str(v).replace(",", "."))) == os_num:
                n += 1
        except ValueError:
            continue
    return n


def anexar_os(os_num: int, registros: list, reutilizando: bool = False) -> int:
    """
    Acrescenta as linhas da OS no FIM da primeira aba (append) — nunca reescreve a planilha.
    Alinha os valores pelo cabeçalho da planilha. Devolve a qtd de linhas da OS confirmadas.
    reutilizando=True: número reservado numa tentativa anterior que pode ter gravado sem confirmar.
    """
    ws = _planilha_gspread().get_worksheet(0)
    cabecalho = ws.row_values(1)

    faltando = [c for c in COLUNAS if c not in cabecalho and c not in ("EDITADO_POR", "DATA_EDICAO")]
    if faltando:
        raise ErroGravacaoOS(f"Colunas ausentes no cabeçalho da planilha: {faltando}")
    col_os = cabecalho.index("OS") + 1

    ja_existem = _qtd_linhas_da_os(ws, col_os, os_num)
    if ja_existem:
        if reutilizando and ja_existem == len(registros):
            return ja_existem   # tentativa anterior já gravou; não duplica
        raise ErroGravacaoOS(
            f"A OS {os_num} já existe na planilha ({ja_existem} linha(s)). Sequência dessincronizada "
            f"ou gravação anterior divergente — confira o histórico antes de tentar de novo."
        )

    linhas = [[_valor_celula({**r, "OS": os_num}.get(col, "")) for col in cabecalho] for r in registros]
    ws.append_rows(linhas, value_input_option="RAW", table_range="A1")

    confirmadas = _qtd_linhas_da_os(ws, col_os, os_num)
    if confirmadas != len(registros):
        raise ErroGravacaoOS(
            f"Confirmação falhou: esperado {len(registros)} linha(s) da OS {os_num}, encontrado {confirmadas}."
        )
    return confirmadas


class ConflitoEdicao(ErroGravacaoOS):
    """A linha mudou na planilha depois que o admin abriu a edição. Nada foi gravado."""


def _txt(v) -> str:
    """Texto de uma célula para exibir em campos; vazio/NaN viram ''. (str(NaN) daria 'nan'.)"""
    v = _valor_celula(v)
    return "" if v == "" else str(v)


def _txt_numero(v) -> str:
    """Telefone/ano que a planilha guarda como número: sem '.0' (21989119085.0 -> '21989119085'). Vazio/NaN -> '—'."""
    v = _valor_celula(v)
    if v == "":
        return "—"
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v)


def _num_float(v, padrao: float = 0.0) -> float:
    """Número ou o padrão. Ao contrário de `x or padrao`, trata NaN corretamente (NaN é 'verdadeiro')."""
    n = pd.to_numeric(v, errors="coerce")
    return float(padrao) if pd.isna(n) else float(n)


def _num_int(v, padrao: int = 0) -> int:
    n = pd.to_numeric(v, errors="coerce")
    return int(padrao) if pd.isna(n) else int(n)


def _norm(v) -> str:
    """Normaliza um valor de célula para COMPARAÇÃO: sem espaços nas pontas e sem '.0' em inteiros."""
    v = _valor_celula(v)
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, (int, float)):
        return str(int(v)) if float(v).is_integer() else repr(float(v))
    texto = str(v).strip()
    try:
        n = float(texto)
        return str(int(n)) if n.is_integer() else repr(n)
    except ValueError:
        return texto


def _ler_linhas_da_os(ws, os_num: int):
    """Lê a aba com valores NÃO formatados. Devolve (cabeçalho, [(nº da linha na planilha, {coluna: valor normalizado}), ...])."""
    todas = ws.get_all_values(value_render_option=gspread.utils.ValueRenderOption.unformatted)
    if not todas or "OS" not in todas[0]:
        raise ErroGravacaoOS("A primeira aba não tem a coluna 'OS' no cabeçalho.")
    cab  = todas[0]
    i_os = cab.index("OS")
    achadas = []
    for n, linha in enumerate(todas[1:], start=2):
        bruto = linha[i_os] if len(linha) > i_os else ""
        try:
            if int(float(bruto)) != os_num:
                continue
        except (TypeError, ValueError):
            continue
        achadas.append((n, {c: _norm(linha[j]) if j < len(linha) else "" for j, c in enumerate(cab) if c}))
    return cab, achadas


def snapshot_linha_os(os_num: int, k: int) -> dict:
    """
    'Foto' da k-ésima linha da OS (na ordem da planilha), tirada quando a edição é aberta.
    Guarda o nº real da linha na planilha — não a posição no DataFrame, que não é confiável.
    """
    ws = _planilha_gspread().get_worksheet(0)
    _, achadas = _ler_linhas_da_os(ws, os_num)
    if k >= len(achadas):
        raise ConflitoEdicao(f"A OS {os_num} tem {len(achadas)} linha(s) na planilha agora; a linha {k + 1} não existe mais.")
    n, valores = achadas[k]
    return {"linha": n, "valores": valores}


def atualizar_linha_os(snap: dict, alteracoes: dict) -> None:
    """
    Grava SOMENTE as células alteradas da linha da OS, numa única chamada, sem tocar no resto da planilha.
    Antes, confere se a linha ainda é idêntica à 'foto' de quando a edição foi aberta; se outra pessoa
    mexeu, levanta ConflitoEdicao e não grava nada.
    """
    ws  = _planilha_gspread().get_worksheet(0)
    cab = ws.row_values(1)
    n   = snap["linha"]

    faixa = f"A{n}:{gspread.utils.rowcol_to_a1(n, max(len(cab), 1))}"
    atual = ws.get(faixa, value_render_option=gspread.utils.ValueRenderOption.unformatted)
    linha = atual[0] if atual else []
    agora = {c: (_norm(linha[j]) if j < len(linha) else "") for j, c in enumerate(cab) if c}
    mudaram = [c for c, v in snap["valores"].items() if agora.get(c, "") != v]
    if mudaram:
        raise ConflitoEdicao(
            "Esta linha da OS foi alterada por outra pessoa depois que você abriu a edição "
            f"(campos: {', '.join(mudaram)}). Nada foi gravado. Clique em BUSCAR OS para recarregar."
        )

    for col in ("EDITADO_POR", "DATA_EDICAO"):          # colunas de auditoria podem ainda não existir
        if col in alteracoes and col not in cab:
            ws.update_cell(1, len(cab) + 1, col)
            cab.append(col)
    faltando = [c for c in alteracoes if c not in cab]
    if faltando:
        raise ErroGravacaoOS(f"Colunas ausentes no cabeçalho da planilha: {faltando}")

    dados = [{"range": gspread.utils.rowcol_to_a1(n, cab.index(c) + 1), "values": [[_valor_celula(v)]]}
             for c, v in alteracoes.items()]
    ws.batch_update(dados, value_input_option="RAW")


def diagnosticar_qualidade_dados(df: pd.DataFrame) -> dict:
    """
    Verifica a integridade dos dados vindos do Google Sheets.

    Os formulários do app (REGISTRAR O.S / EDITAR O.S) usam number_input
    com min_value=0.0, então NUNCA produzem texto ou valor negativo em
    CUSTO/PAGAMENTO. Se este tipo de inconsistência aparecer, a causa é
    edição manual da planilha por fora do app — o Google Sheets não impõe
    nenhum schema ou tipo de dado. Esta função existe para tornar esse
    problema estrutural visível, em vez de deixá-lo mascarado por
    `errors='coerce'` em cálculos financeiros.
    """
    problemas = []

    if df.empty:
        return {"total": 0, "detalhes": pd.DataFrame(columns=["OS", "CAMPO", "PROBLEMA"])}

    # --- Datas não reconhecíveis ---
    datas = pd.to_datetime(df['DATA'], errors='coerce')
    mask_data_ruim = datas.isna() & df['DATA'].notna() & (df['DATA'].astype(str).str.strip() != "")
    for idx in df.index[mask_data_ruim]:
        problemas.append({"OS": df.loc[idx, 'OS'], "CAMPO": "DATA",
                           "PROBLEMA": f"valor não reconhecido: '{df.loc[idx, 'DATA']}'"})

    # --- Custo / Pagamento não numéricos ou negativos ---
    for campo in ('CUSTO (R$)', 'PAGAMENTO (R$)'):
        numeros = pd.to_numeric(df[campo], errors='coerce')

        mask_nao_numerico = numeros.isna() & df[campo].notna() & (df[campo].astype(str).str.strip() != "")
        for idx in df.index[mask_nao_numerico]:
            problemas.append({"OS": df.loc[idx, 'OS'], "CAMPO": campo,
                               "PROBLEMA": f"não numérico: '{df.loc[idx, campo]}'"})

        mask_negativo = numeros < 0
        for idx in df.index[mask_negativo.fillna(False)]:
            problemas.append({"OS": df.loc[idx, 'OS'], "CAMPO": campo,
                               "PROBLEMA": f"valor negativo: {numeros[idx]}"})

    # --- Números de OS duplicados (colisão do max()+1 sob concorrência) ---
    # ATENÇÃO: uma mesma OS pode ter várias linhas LEGITIMAMENTE, quando o
    # atendimento envolve múltiplos serviços — ver gerar_pdf_os(), que já
    # assume "linhas_os" no plural para uma mesma OS. Duplicidade só é
    # sintoma de corrupção real quando o mesmo número de OS aparece em
    # veículos DIFERENTES (placa ou chassi divergentes dentro do mesmo
    # número) — isso sim indica colisão de geração concorrente.
    os_num = pd.to_numeric(df['OS'], errors='coerce')
    df_os_valido = df[os_num.notna()].copy()
    df_os_valido['_OS_NUM'] = os_num[os_num.notna()]

    for os_val, grupo in df_os_valido.groupby('_OS_NUM'):
        if len(grupo) <= 1:
            continue
        placas  = grupo['PLACA'].astype(str).str.strip().str.upper().replace({"NAN": ""}).unique()
        chassis = grupo['CHASSI'].astype(str).str.strip().str.upper().replace({"NAN": ""}).unique()
        placas  = [p for p in placas if p]
        chassis = [c for c in chassis if c]
        if len(placas) > 1 or len(chassis) > 1:
            problemas.append({
                "OS": os_val, "CAMPO": "OS",
                "PROBLEMA": f"mesmo número de OS usado em veículos diferentes "
                            f"(placas: {', '.join(placas) if placas else '—'}) — colisão de geração de número"
            })

    detalhes = pd.DataFrame(problemas, columns=["OS", "CAMPO", "PROBLEMA"])
    return {"total": len(problemas), "detalhes": detalhes}

# ---------------------------------------------------------------------------
# GERAÇÃO DE PDF DA O.S
# ---------------------------------------------------------------------------
def gerar_pdf_os(linhas_os: pd.DataFrame) -> bytes:
    """
    Recebe todas as linhas de uma OS (pode ter múltiplos serviços)
    e retorna os bytes do PDF gerado.
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=1.8*cm, rightMargin=1.8*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm
    )

    styles = getSampleStyleSheet()
    s_titulo = ParagraphStyle("titulo", fontSize=18, fontName="Helvetica-Bold",
                               alignment=TA_CENTER, spaceAfter=2)
    s_sub = ParagraphStyle("sub", fontSize=10, fontName="Helvetica",
                        alignment=TA_CENTER, textColor=colors.HexColor("#555555"), spaceAfter=20)
    s_label  = ParagraphStyle("label",  fontSize=8,  fontName="Helvetica-Bold",
                               textColor=colors.HexColor("#333333"))
    s_valor  = ParagraphStyle("valor",  fontSize=9,  fontName="Helvetica")
    s_secao  = ParagraphStyle("secao",  fontSize=10, fontName="Helvetica-Bold",
                               textColor=colors.HexColor("#1a1a2e"), spaceBefore=10, spaceAfter=4)

    # Pega dados do primeiro registro (dados do veículo são iguais em todas as linhas)
    r = linhas_os.iloc[0]

    def val(campo, inteiro=False):
        v = r.get(campo, "")
        if pd.isna(v) or str(v).strip() in ("", "nan"):
            return "—"
        if inteiro:
            try:
                return str(int(float(v)))
            except Exception:
                pass
        return str(v)

    try:
        data_fmt = pd.to_datetime(r['DATA']).strftime("%d/%m/%Y")
    except Exception:
        data_fmt = val('DATA')

    num_os = val('OS', inteiro=True)
    story  = []

    # ── Cabeçalho ──────────────────────────────────────────────────────────
    story.append(Paragraph("SGM AUTOMOTIVA", s_titulo))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Sistema de Gestão Mecânica Automotiva", s_sub))
    story.append(HRFlowable(width="100%", thickness=1.5,
                             color=colors.HexColor("#1a1a2e"), spaceAfter=8))

    # Número da OS + Data
    os_data = Table(
        [[Paragraph(f"ORDEM DE SERVIÇO Nº  {num_os}", ParagraphStyle(
              "osnum", fontSize=13, fontName="Helvetica-Bold",
              textColor=colors.HexColor("#1a1a2e"))),
          Paragraph(f"Data: {data_fmt}", ParagraphStyle(
              "data", fontSize=10, fontName="Helvetica",
              alignment=TA_LEFT))]],
        colWidths=["60%", "40%"]
    )
    os_data.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(os_data)
    story.append(Spacer(1, 6))

    # ── Dados do Veículo ───────────────────────────────────────────────────
    story.append(Paragraph("DADOS DO VEÍCULO E PROPRIETÁRIO", s_secao))

    veiculo_data = [
        ["PROPRIETÁRIO", val('PROPRIETÁRIO'), "PLACA", val('PLACA')],
        ["MARCA / MODELO", f"{val('MARCA')} {val('MODELO')}", "ANO", val('ANO DE FABRICAÇÃO', inteiro=True)],
        ["KM ATUAL", val('KM ATUAL', inteiro=True), "CHASSI", val('CHASSI')],
        ["MECÂNICO", val('MECÂNICO'), "", ""],
    ]

    t_veiculo = Table(
        [[Paragraph(c[0], s_label), Paragraph(c[1], s_valor),
          Paragraph(c[2], s_label), Paragraph(c[3], s_valor)]
         for c in veiculo_data],
        colWidths=["22%", "28%", "22%", "28%"]
    )
    t_veiculo.setStyle(TableStyle([
    ("BACKGROUND",    (0,0), (0,-1), colors.HexColor("#f0f2f6")),
    ("BACKGROUND",    (2,0), (2,-1), colors.HexColor("#f0f2f6")),
    ("BOX",           (0,0), (-1,-1), 0.5, colors.HexColor("#cccccc")),
    ("INNERGRID",     (0,0), (-1,-1), 0.3, colors.HexColor("#dddddd")),
    ("TOPPADDING",    (0,0), (-1,-1), 5),
    ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ("LEFTPADDING",   (0,0), (-1,-1), 6),
    ("SPAN",          (1,3), (3,3)),   # ← ADICIONAR: valor do mecânico ocupa colunas 1 a 3
]))
    story.append(t_veiculo)
    story.append(Spacer(1, 8))

    # ── Serviços (uma linha por serviço da OS) ─────────────────────────────
    story.append(Paragraph("SERVIÇOS EXECUTADOS", s_secao))

    cab = [
        Paragraph("SERVIÇO / DEFEITO",   ParagraphStyle("h", fontSize=8, fontName="Helvetica-Bold", textColor=colors.white)),
        Paragraph("DIAGNÓSTICO",          ParagraphStyle("h", fontSize=8, fontName="Helvetica-Bold", textColor=colors.white)),
        Paragraph("SERVIÇO EXECUTADO",    ParagraphStyle("h", fontSize=8, fontName="Helvetica-Bold", textColor=colors.white)),
        Paragraph("CUSTO",                ParagraphStyle("h", fontSize=8, fontName="Helvetica-Bold", textColor=colors.white)),
        Paragraph("PAGO",                 ParagraphStyle("h", fontSize=8, fontName="Helvetica-Bold", textColor=colors.white)),
    ]
    rows = [cab]
    total_custo = 0.0
    total_pago  = 0.0

    for _, srv in linhas_os.iterrows():
        def sv(c):
            v = srv.get(c, "")
            return str(v) if pd.notna(v) and str(v).strip() not in ("", "nan") else "—"

        custo = _num_float(srv.get('CUSTO (R$)'))
        pago  = _num_float(srv.get('PAGAMENTO (R$)'))
        total_custo += custo
        total_pago  += pago

        rows.append([
            Paragraph(f"{sv('SERVIÇO')}\n{sv('DEFEITO')}", s_valor),
            Paragraph(sv('DIAGNÓSTICO'),       s_valor),
            Paragraph(sv('SERVIÇO EXECUTADO'), s_valor),
            Paragraph(f"R$ {custo:,.2f}",      s_valor),
            Paragraph(f"R$ {pago:,.2f}",       s_valor),
        ])

    # Linha de totais
    rows.append([
        Paragraph("", s_valor),
        Paragraph("", s_valor),
        Paragraph("TOTAL", ParagraphStyle("tot", fontSize=9, fontName="Helvetica-Bold", alignment=TA_LEFT)),
        Paragraph(f"R$ {total_custo:,.2f}", ParagraphStyle("tot", fontSize=9, fontName="Helvetica-Bold")),
        Paragraph(f"R$ {total_pago:,.2f}",  ParagraphStyle("tot", fontSize=9, fontName="Helvetica-Bold")),
    ])

    t_serv = Table(rows, colWidths=["22%", "26%", "26%", "13%", "13%"])
    t_serv.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  colors.HexColor("#1a1a2e")),
        ("BACKGROUND",    (0,-1),(-1,-1), colors.HexColor("#e8eaf0")),
        ("BOX",           (0,0), (-1,-1), 0.5, colors.HexColor("#aaaaaa")),
        ("INNERGRID",     (0,0), (-1,-1), 0.3, colors.HexColor("#dddddd")),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 5),
        ("LINEABOVE",     (0,-1),(-1,-1), 1,   colors.HexColor("#1a1a2e")),
    ]))
    story.append(t_serv)

    # ── Assinaturas ────────────────────────────────────────────────────────
    story.append(Spacer(1, 24))
    story.append(HRFlowable(width="100%", thickness=0.5,
                             color=colors.HexColor("#cccccc"), spaceAfter=12))

    s_ass = ParagraphStyle("ass", fontSize=9, fontName="Helvetica", alignment=TA_CENTER, leading=16)
    ass = Table(
        [[Paragraph("_______________________________<br/><br/>Assinatura do Cliente", s_ass),
          Paragraph("_______________________________<br/><br/>Responsável Técnico", s_ass)]],
        colWidths=["50%", "50%"]
    )
    story.append(ass)

    # ── Rodapé ─────────────────────────────────────────────────────────────
    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=0.5,
                             color=colors.HexColor("#cccccc"), spaceAfter=4))
    story.append(Paragraph(
        f"SGM Automotiva · OS Nº {num_os} · Emitido em {agora().strftime('%d/%m/%Y %H:%M')}",
        ParagraphStyle("rodape", fontSize=7, fontName="Helvetica",
                        textColor=colors.HexColor("#999999"), alignment=TA_CENTER)
    ))

    doc.build(story)
    return buf.getvalue()

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
        "AR NÃO VENTILA",
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
        "PUXANDO PARA DIREITA",
        "PUXANDO PARA DIREITA",
        "VAZAMENTO DE ÓLEO HIDRÁULICO",
        "VOLANTE COM FOLGA EXCESSIVA",
        "OUTROS",
    ],
    "EMBREAGEM": [
        "DISCO DE EMBREAGEM DESGASTADO",
        "EMBREAGEM COM BARULHO",
        "EMBREAGEM NÃO DESACOPLANDO",
        "EMBREAGEM PATINANDO",
        "FLUIDO DE FREIO BAIXO",
        "PEDAL DURO",
        "PEDAL MOLE",
        "PLATO DE EMBREAGEM COM DEFEITO",
        "VIBRAÇÃO AO ACIONAR EMBREAGEM",
        "OUTROS",
    ],
    "FREIOS": [
        "CILINDRO MESTRE COM DEFEITO",
        "DISCO DE FREIO DESGASTADO",
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
        "REVISÃO DE LANTERNAGEM"
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
        "RELES COM DEFEITO",
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

LISTA_MECANICOS = ["MECÂNICO1", "MECÂNICO2", "MECÂNICO3"]

LISTA_MARCA = [
    "AUDI", "BMW", "BYD", "CHEVROLET", "CITROËN", "FIAT", "FORD",
    "HONDA", "HYUNDAI", "INFINITI", "JAGUAR", "JEEP", "LEXUS", "MAZDA",
    "MERCEDES-BENZ", "MITSUBISHI", "NISSAN", "RENAULT", "TOYOTA",
    "VOLKSWAGEN", "OUTRO"
]


# ---------------------------------------------------------------------------
# PERFIS DE ACESSO
# Administradores: acesso total.
# Mecânicos: só veem as próprias OS e não acessam o financeiro completo.
# ---------------------------------------------------------------------------
PERFIS = {
    "admin":    ["jonascosta"],
    "mecanico: ["mecanico1"],
}

def perfil_do_usuario(usuario: str) -> str:
    for perfil, lista in PERFIS.items():
        if usuario in lista:
            return perfil
    return "mecanico"   # padrão mais restritivo

# Mapa username → nome real do mecânico (para filtro correto)
USUARIO_PARA_MECANICO = {
    "jonascosta":   "JONAS COSTA",
    "mecanico1":  "mecanico1",
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

            if usuario_input in usuarios:
                ok, motivo = _verificar_senha(senha_input, usuarios[usuario_input])
                if ok:
                    st.session_state.logado         = True
                    st.session_state.usuario_nome   = usuario_input
                    st.session_state.usuario_perfil = perfil_do_usuario(usuario_input)
                    st.rerun()
                else:
                    st.sidebar.error("Usuário ou senha inválidos.")
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
                        ORDENS DE SERVIÇO, HISTÓRICO DE VEÍCULOS E CONTROLE FINANCEIRO DA SUA OFICINA.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.info("Utilize seu usuário e senha na barra lateral para acessar o sistema.")

            c1, c2, c3 = st.columns(3)
            c1.metric("Status",  "Online")
            c2.metric("Versão",  APP_VERSAO)
            c3.metric("Suporte", "Ativo")

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
    # Aplica redirecionamento de menu pendente (definido em telas anteriores),
    # ANTES do selectbox ser instanciado nesta execução — não pode ser feito depois.
    if "forcar_menu" in st.session_state:
        st.session_state["menu_nav"] = st.session_state.pop("forcar_menu")

    if perfil == "admin":
        menu = ["REGISTRAR O.S", "SOLICITAÇÕES DE CLIENTES", "EDITAR O.S", "HISTÓRICO E FINANCEIRO", "SOBRE O APP"]
    else:
        menu = ["REGISTRAR O.S", "MINHAS ORDENS DE SERVIÇO", "SOBRE O APP"]

    escolha = st.sidebar.selectbox("MENU DE NAVEGAÇÃO:", menu, key="menu_nav")

    df = carregar_dados()

    if perfil == "admin":
        _diag = diagnosticar_qualidade_dados(df)
        if _diag["total"] > 0:
            with st.sidebar.expander(f"⚠️ {_diag['total']} inconsistência(s) nos dados", expanded=False):
                st.caption("Detectado(s) na planilha — não podem ter vindo dos formulários do app.")
                st.dataframe(_diag["detalhes"], hide_index=True, use_container_width=True)

    # -----------------------------------------------------------------------
    # TELA: REGISTRAR O.S
    # -----------------------------------------------------------------------
    if escolha == "REGISTRAR O.S":
        st.subheader("📝 REGISTRAR ORDEM DE SERVIÇO")

        if "lista_servicos_temp" not in st.session_state:
            st.session_state.lista_servicos_temp = []

        # Número da próxima OS — estimativa para exibição
        # O número definitivo é recalculado no momento do salvamento
        proxima_os = estimar_proxima_os(df)
        st.info(f"📌 ORDEM DE SERVIÇO ESTIMADA: **{proxima_os}** *(confirmada ao salvar)*")

        travado = len(st.session_state.lista_servicos_temp) > 0

        col1, col2 = st.columns(2)
        with col1:
            data_input        = st.date_input("DATA DO SERVIÇO", hoje(), disabled=travado)
            marca_input       = st.selectbox("MARCA", LISTA_MARCA, disabled=travado)
            modelo_input      = st.text_input("MODELO", disabled=travado, key="modelo")
            km_input          = st.number_input("KM ATUAL", min_value=0, step=1, format="%d", disabled=travado, key="km")
        with col2:
            proprietario_input = st.text_input("PROPRIETÁRIO", disabled=travado, key="prop")
            placa_input        = st.text_input("PLACA", disabled=travado, key="placa").upper()
            ano_input          = st.number_input("ANO DE FABRICAÇÃO", min_value=1910, max_value=hoje().year + 1, step=1, format="%d", disabled=travado, key="ano")
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
                })
                st.session_state.pop("os_reservada", None)
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
                # Só mostra o botão FINALIZAR se ainda não está aguardando confirmação
                if not st.session_state.get("confirmar_salvar"):
                    if st.button("💾 FINALIZAR E SALVAR NA NUVEM", type="primary", use_container_width=True):
                        st.session_state.confirmar_salvar = True
                        st.rerun()

            with col_btn2:
                if st.button("🗑️ DESCARTAR OS", use_container_width=True):
                    st.session_state.lista_servicos_temp = []
                    st.session_state.pop("confirmar_salvar", None)
                    st.session_state.pop("os_reservada", None)
                    st.rerun()

            # Bloco de confirmação — aparece abaixo dos botões, fora de qualquer coluna
            if st.session_state.get("confirmar_salvar"):
                st.warning("⚠️ Confirma o salvamento desta OS? A operação não pode ser desfeita.")
                cc1, cc2 = st.columns(2)

                with cc1:
                    if st.button("✅ SIM, SALVAR", type="primary", use_container_width=True):
                        with st.status("📦 ENVIANDO PARA GOOGLE SHEETS...", expanded=True) as status:
                            try:
                                registros    = list(st.session_state.lista_servicos_temp)
                                os_definitiva = st.session_state.get("os_reservada")
                                reutilizando  = os_definitiva is not None
                                if not reutilizando:
                                    os_definitiva = reservar_numero_os(nome)
                                    st.session_state.os_reservada = os_definitiva

                                anexar_os(os_definitiva, registros, reutilizando)

                                df_temp = pd.DataFrame(registros)
                                df_temp['OS'] = os_definitiva
                                status.update(label="✅ OS SALVA COM SUCESSO!", state="complete", expanded=False)
                                st.session_state.lista_servicos_temp = []
                                st.session_state.confirmar_salvar    = False
                                st.session_state.pop("os_reservada", None)
                                st.session_state.os_recém_salva      = os_definitiva
                                st.session_state.df_os_recém_salva   = df_temp.to_dict("records")
                                st.balloons()
                                st.rerun()

                            except Exception as e:
                                st.error(f"❌ Erro ao salvar: {e}")
                                status.update(label="❌ Falha no envio.", state="error")

                with cc2:
                    if st.button("❌ CANCELAR", use_container_width=True):
                        st.session_state.confirmar_salvar = False
                        st.rerun()

        # --- Botão de impressão da OS recém-salva ---
        os_recente = st.session_state.get("os_recém_salva")
        df_recente = st.session_state.get("df_os_recém_salva")
        if os_recente and df_recente:
            st.success(f"✅ OS **{os_recente}** salva com sucesso!")
            st.markdown("### 🖨️ IMPRIMIR ORDEM DE SERVIÇO")
            try:
                pdf_bytes = gerar_pdf_os(pd.DataFrame(df_recente))
                st.download_button(
                    label=f"📄 BAIXAR PDF — OS Nº {os_recente}",
                    data=pdf_bytes,
                    file_name=f"OS_{os_recente}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary",
                )
            except Exception as e:
                st.error(f"Erro ao gerar PDF: {e}")
            if st.button("✖️ Fechar", use_container_width=False):
                st.session_state.pop("os_recém_salva", None)
                st.session_state.pop("df_os_recém_salva", None)
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
                st.session_state.pop("edit_snap", None)
                st.session_state.pop("edit_snap_chave", None)

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
                    k   = list(linhas.index).index(idx_escolhido)   # posição desta linha entre as linhas da mesma OS
                    sfx = f"{os_buscada}_{k}"                       # chaves únicas por OS/linha: sem isso o formulário herda valores da OS anterior

                    st.markdown(f"---\n### 📋 Editando OS **{os_buscada}**")

                    # 'Foto' da linha na planilha no momento em que a edição foi aberta
                    chave_snap = (os_buscada, k)
                    snap = None
                    if st.session_state.get("edit_snap_chave") == chave_snap:
                        snap = st.session_state.get("edit_snap")
                    else:
                        try:
                            snap = snapshot_linha_os(os_buscada, k)
                            for campo in ("PLACA", "SERVIÇO"):
                                if _norm(row[campo]) != snap["valores"].get(campo, ""):
                                    raise ConflitoEdicao("Os dados exibidos não batem com a planilha (ela mudou agora há pouco).")
                            st.session_state.edit_snap       = snap
                            st.session_state.edit_snap_chave = chave_snap
                        except Exception as e:
                            snap = None
                            st.error(f"❌ Não foi possível abrir esta OS para edição com segurança: {e} Clique em BUSCAR OS para tentar de novo.")

                    # Última edição (auditoria)
                    if _txt(row.get('EDITADO_POR')).strip():
                        st.caption(f"📝 Última edição por **{row['EDITADO_POR']}** em {row['DATA_EDICAO']}")

                    dt_ini   = pd.to_datetime(row['DATA'], errors='coerce')
                    data_ini = dt_ini.date() if pd.notna(dt_ini) else hoje()
                    marca_ini = row['MARCA'] if row['MARCA'] in LISTA_MARCA else LISTA_MARCA[-1]
                    km_ini    = _num_int(row['KM ATUAL'])
                    ano_ini   = max(1910, min(_num_int(row['ANO DE FABRICAÇÃO'], 2000), hoje().year + 1))

                    col1, col2 = st.columns(2)
                    with col1:
                        e_data   = st.date_input("DATA DO SERVIÇO", value=data_ini, key=f"e_data_{sfx}")
                        e_marca  = st.selectbox("MARCA", LISTA_MARCA, index=LISTA_MARCA.index(marca_ini), key=f"e_marca_{sfx}")
                        e_modelo = st.text_input("MODELO", value=_txt(row['MODELO']), key=f"e_modelo_{sfx}")
                        e_km     = st.number_input("KM ATUAL", min_value=0, step=1, value=km_ini,
                                                   format="%d", key=f"e_km_{sfx}")
                    with col2:
                        e_prop   = st.text_input("PROPRIETÁRIO", value=_txt(row['PROPRIETÁRIO']), key=f"e_prop_{sfx}")
                        e_placa  = st.text_input("PLACA", value=_txt(row['PLACA']), key=f"e_placa_{sfx}").upper()
                        e_ano    = st.number_input("ANO DE FABRICAÇÃO", min_value=1910,
                                                   max_value=hoje().year + 1, step=1, value=ano_ini,
                                                   format="%d", key=f"e_ano_{sfx}")
                        e_chassi = st.text_input("CHASSI", value=_txt(row['CHASSI']), key=f"e_chassi_{sfx}").upper()

                    st.divider()
                    serv_ini  = row['SERVIÇO'] if row['SERVIÇO'] in LISTA_SERVICOS else LISTA_SERVICOS[0]
                    custo_ini = _num_float(row['CUSTO (R$)'])
                    pgto_ini  = _num_float(row['PAGAMENTO (R$)'])
                    mec_ini   = row['MECÂNICO'] if row['MECÂNICO'] in LISTA_MECANICOS else LISTA_MECANICOS[0]
                    c1, c2, c3, c4 = st.columns([4, 3, 2, 2])
                    with c1:
                        e_servico = st.selectbox("GRUPO DO SERVIÇO", LISTA_SERVICOS, index=LISTA_SERVICOS.index(serv_ini), key=f"e_servico_{sfx}")
                    with c2:
                        e_custo = st.number_input("CUSTO DO REPARO (R$)", min_value=0.0, step=10.0, format="%.2f",
                                                  value=custo_ini, key=f"e_custo_{sfx}")
                    with c3:
                        e_pgto  = st.number_input("PAGAMENTO RECEBIDO (R$)", min_value=0.0, step=10.0, format="%.2f",
                                                  value=pgto_ini, key=f"e_pgto_{sfx}")
                    with c4:
                        e_mec   = st.selectbox("MECÂNICO RESPONSÁVEL", LISTA_MECANICOS, index=LISTA_MECANICOS.index(mec_ini), key=f"e_mec_{sfx}")

                    # Defeito filtrado pelo serviço escolhido
                    defeitos_ed = DEFEITOS_POR_SERVICO.get(e_servico, ["ESPECIFICAR NO CAMPO DE DIAGNÓSTICO"])
                    def_ini   = row['DEFEITO'] if row['DEFEITO'] in defeitos_ed else defeitos_ed[0]
                    e_defeito = st.selectbox("🔎 DEFEITO IDENTIFICADO", defeitos_ed, index=defeitos_ed.index(def_ini), key=f"e_defeito_{sfx}")

                    st.markdown("---")
                    col_d1, col_d2 = st.columns(2)
                    with col_d1:
                        e_diag = st.text_area("🩺 DIAGNÓSTICO DO MECÂNICO", value=_txt(row['DIAGNÓSTICO']), key=f"e_diag_{sfx}")
                    with col_d2:
                        e_exec = st.text_area("🔧 SERVIÇO EXECUTADO", value=_txt(row['SERVIÇO EXECUTADO']), key=f"e_exec_{sfx}")

                    # Só o que o admin REALMENTE mudou é gravado (campo = (valor novo, valor com que o formulário abriu))
                    campos = {
                        'DATA':              (str(e_data),        str(data_ini)),
                        'MARCA':             (e_marca,            marca_ini),
                        'MODELO':            (e_modelo.strip(),   _txt(row['MODELO'])),
                        'KM ATUAL':          (e_km,               km_ini),
                        'PROPRIETÁRIO':      (e_prop.strip(),     _txt(row['PROPRIETÁRIO'])),
                        'PLACA':             (e_placa.strip(),    _txt(row['PLACA'])),
                        'ANO DE FABRICAÇÃO': (e_ano,              ano_ini),
                        'CHASSI':            (e_chassi.strip(),   _txt(row['CHASSI'])),
                        'SERVIÇO':           (e_servico,          serv_ini),
                        'DEFEITO':           (e_defeito,          def_ini),
                        'DIAGNÓSTICO':       (e_diag.strip(),     _txt(row['DIAGNÓSTICO'])),
                        'SERVIÇO EXECUTADO': (e_exec.strip(),     _txt(row['SERVIÇO EXECUTADO'])),
                        'CUSTO (R$)':        (e_custo,            custo_ini),
                        'PAGAMENTO (R$)':    (e_pgto,             pgto_ini),
                        'MECÂNICO':          (e_mec,              mec_ini),
                    }
                    alteracoes = {c: novo for c, (novo, antigo) in campos.items() if _norm(novo) != _norm(antigo)}

                    st.markdown("---")
                    if st.button("💾 SALVAR ALTERAÇÕES", type="primary", use_container_width=True, disabled=snap is None):
                        erros_ed = []
                        if not e_placa.strip():   erros_ed.append("Placa")
                        if not e_modelo.strip():  erros_ed.append("Modelo")
                        if not e_diag.strip():    erros_ed.append("Diagnóstico")
                        if not e_exec.strip():    erros_ed.append("Serviço Executado")

                        if erros_ed:
                            st.error(f"⚠️ Campos obrigatórios: {', '.join(erros_ed)}.")
                        elif not alteracoes:
                            st.info("Nenhum campo foi alterado — não há nada para salvar.")
                        else:
                            st.session_state.confirmar_edicao = True

                    if st.session_state.get("confirmar_edicao") and snap is not None:
                        st.warning(f"⚠️ Confirma a alteração desta OS? Serão gravados apenas: {', '.join(alteracoes) or '—'}.")
                        cc1, cc2 = st.columns(2)
                        with cc1:
                            if st.button("✅ SIM, ALTERAR", use_container_width=True, key="btn_sim_edit"):
                                with st.status("📦 ATUALIZANDO NO GOOGLE SHEETS...", expanded=True) as s_edit:
                                    try:
                                        if not alteracoes:
                                            raise ErroGravacaoOS("Nenhum campo alterado.")
                                        carimbo = agora().strftime("%d/%m/%Y %H:%M")
                                        atualizar_linha_os(snap, {**alteracoes, 'EDITADO_POR': nome, 'DATA_EDICAO': carimbo})
                                        s_edit.update(label="✅ OS ATUALIZADA COM SUCESSO!", state="complete", expanded=False)
                                        for chave in ("os_buscada", "confirmar_edicao", "edit_snap", "edit_snap_chave"):
                                            st.session_state.pop(chave, None)
                                        st.balloons()
                                        st.rerun()
                                    except ConflitoEdicao as e:
                                        st.error(f"⚠️ {e}")
                                        s_edit.update(label="⚠️ Não gravado: a linha mudou.", state="error")
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
            mecanico_nome = USUARIO_PARA_MECANICO.get(nome, nome.upper())
            if perfil == "mecanico":
                df = df[df['MECÂNICO'].astype(str).str.upper() == mecanico_nome]

            df['DATA_DT'] = pd.to_datetime(df['DATA'], errors='coerce')

            st.markdown("### 📊 FILTROS DE BUSCA")

            # Intervalo de datas (substitui os 3 selects separados)
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                data_inicio = st.date_input("DATA INICIAL", value=date(2020, 1, 1))
            with col_d2:
                data_fim = st.date_input("DATA FINAL", value=hoje())

            c_busca1, c_busca2, c_busca3 = st.columns([2, 1, 1])
            with c_busca1:
                busca_placa_os = st.text_input("BUSCAR POR PLACA OU OS:").upper()
            with c_busca2:
                opcoes_mec = ["Todos"] + LISTA_MECANICOS if perfil == "admin" else [mecanico_nome]   # nome REAL do mecânico, não o login
                filtro_mec = st.selectbox("FILTRAR POR MECÂNICO", opcoes_mec)

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
                df_f = df_f[df_f['MECÂNICO'].astype(str).str.upper() == filtro_mec.upper()]

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

                st.write("---")
                st.markdown("### 📅 TOTAIS POR MÊS")

                # Linhas com DATA inválida (NaT) não podem ser atribuídas a nenhum mês.
                qtd_data_invalida = df_f['DATA_DT'].isna().sum()

                # Valores de custo/pagamento não numéricos viram NaN e são tratados como 0 na soma.
                custo_num = pd.to_numeric(df_f['CUSTO (R$)'], errors='coerce')
                pagto_num = pd.to_numeric(df_f['PAGAMENTO (R$)'], errors='coerce')
                qtd_custo_invalido = df_f['CUSTO (R$)'].notna().sum() - custo_num.notna().sum()
                qtd_pagto_invalido = df_f['PAGAMENTO (R$)'].notna().sum() - pagto_num.notna().sum()

                if qtd_data_invalida or qtd_custo_invalido or qtd_pagto_invalido:
                    avisos = []
                    if qtd_data_invalida:
                        avisos.append(f"{qtd_data_invalida} linha(s) com DATA inválida/vazia (excluídas do resumo mensal)")
                    if qtd_custo_invalido:
                        avisos.append(f"{qtd_custo_invalido} linha(s) com CUSTO não numérico (tratado como R$ 0,00)")
                    if qtd_pagto_invalido:
                        avisos.append(f"{qtd_pagto_invalido} linha(s) com PAGAMENTO não numérico (tratado como R$ 0,00)")
                    st.warning("⚠️ Inconsistências encontradas nos dados: " + "; ".join(avisos) + ".")

                df_mensal = df_f.dropna(subset=['DATA_DT']).copy()

                if df_mensal.empty:
                    st.info("Nenhum registro com data válida no período filtrado.")
                else:
                    df_mensal['CUSTO_NUM']    = pd.to_numeric(df_mensal['CUSTO (R$)'], errors='coerce').fillna(0)
                    df_mensal['PAGAMENTO_NUM'] = pd.to_numeric(df_mensal['PAGAMENTO (R$)'], errors='coerce').fillna(0)
                    # to_period('M') garante ordenação cronológica correta (não alfabética por string).
                    df_mensal['MES_REF'] = df_mensal['DATA_DT'].dt.to_period('M')

                    # Preenche gaps internos (ex: junho sem registro entre maio
                    # e julho) com 0 explícito, mas SOMENTE entre o primeiro e o
                    # último mês que de fato têm dado — nunca usando o filtro de
                    # busca (data_inicio/data_fim), cujo default é 2020 até hoje
                    # e geraria dezenas de linhas zeradas sem necessidade.
                    mes_min = df_mensal['MES_REF'].min()
                    mes_max = df_mensal['MES_REF'].max()
                    periodo_completo = pd.period_range(start=mes_min, end=mes_max, freq='M')
                    tabela_periodo = (
                        df_mensal.groupby('MES_REF')[['PAGAMENTO_NUM', 'CUSTO_NUM']]
                        .sum()
                        .reindex(periodo_completo, fill_value=0)
                    )
                    tabela_periodo['SALDO'] = tabela_periodo['PAGAMENTO_NUM'] - tabela_periodo['CUSTO_NUM']
                    tabela_periodo.index = tabela_periodo.index.strftime('%m/%Y')
                    tabela_periodo.columns = ['Faturamento (R$)', 'Custo (R$)', 'Saldo (R$)']

                    st.dataframe(
                        tabela_periodo,
                        use_container_width=True,
                        column_config={
                            "Faturamento (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                            "Custo (R$)":       st.column_config.NumberColumn(format="R$ %.2f"),
                            "Saldo (R$)":       st.column_config.NumberColumn(format="R$ %.2f"),
                        }
                    )

                    grafico_dados = (
                        tabela_periodo[['Faturamento (R$)', 'Custo (R$)']]
                        .reset_index()
                        .rename(columns={'index': 'Mês'})
                        .melt(id_vars='Mês', var_name='Tipo', value_name='Valor')
                    )

                    grafico = alt.Chart(grafico_dados).mark_bar(size=18).encode(
                        x=alt.X('Mês:N', sort=list(tabela_periodo.index), title=None),
                        y=alt.Y('Valor:Q', title='R$'),
                        color=alt.Color('Tipo:N', title=None),
                        xOffset='Tipo:N',
                        tooltip=['Mês', 'Tipo', alt.Tooltip('Valor:Q', format=',.2f')]
                    ).properties(height=320)

                    st.altair_chart(grafico, use_container_width=True)
            else:
                st.metric("TOTAL DE OS", len(df_f))

            st.write("---")

            colunas_exibir = COLUNAS if perfil == "admin" else [
                'OS', 'DATA', 'MARCA', 'MODELO', 'PLACA', 'SERVIÇO',
                'DEFEITO', 'DIAGNÓSTICO', 'SERVIÇO EXECUTADO'
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

            # --- Reimpressão de OS antiga ---
            st.markdown("---")
            st.markdown("### 🖨️ REIMPRIMIR ORDEM DE SERVIÇO")
            col_re1, col_re2 = st.columns([2, 1])
            with col_re1:
                num_reimp = st.number_input(
                    "NÚMERO DA OS", min_value=1, step=1, format="%d", key="reimp_num",
                    help="Digite o número da OS que deseja reimprimir."
                )
            with col_re2:
                st.markdown("<br>", unsafe_allow_html=True)
                gerar_reimp = st.button("🔍 GERAR PDF", use_container_width=True, key="btn_reimp")

            if gerar_reimp:
                linhas_reimp = df[pd.to_numeric(df['OS'], errors='coerce') == int(num_reimp)]
                if linhas_reimp.empty:
                    st.error(f"⚠️ OS nº {int(num_reimp)} não encontrada.")
                else:
                    try:
                        pdf_bytes = gerar_pdf_os(linhas_reimp)
                        st.download_button(
                            label=f"📄 BAIXAR PDF — OS Nº {int(num_reimp)}",
                            data=pdf_bytes,
                            file_name=f"OS_{int(num_reimp)}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                            type="primary",
                            key="dl_reimp"
                        )
                    except Exception as e:
                        st.error(f"Erro ao gerar PDF: {e}")

    # -----------------------------------------------------------------------
    # TELA: SOLICITAÇÕES DE CLIENTES (somente admin)
    # -----------------------------------------------------------------------
    elif escolha == "SOLICITAÇÕES DE CLIENTES":
        st.subheader("📥 SOLICITAÇÕES DE CLIENTES")
        st.caption("Pedidos enviados pelo formulário público, antes da chegada do veículo na oficina.")

        df_sol = carregar_solicitacoes()

        if df_sol.empty:
            st.info("Nenhuma solicitação registrada ainda.")
        else:
            pendentes = df_sol[df_sol["STATUS"].astype(str).str.strip().str.lower() == "pendente"]

            if pendentes.empty:
                st.success("Nenhuma solicitação pendente no momento.")
            else:
                st.warning(f"⚠️ {len(pendentes)} solicitação(ões) aguardando análise.")

                for idx, row in pendentes.iterrows():
                    with st.expander(f"🔧 {row['NOME']} — Placa {row['PLACA']} — {row['DATA DA SOLICITAÇÃO']}"):
                        st.write(f"**Telefone:** {_txt_numero(row['TELEFONE'])}")
                        st.write(f"**Placa:** {row['PLACA']}")
                        st.write(f"**Defeito relatado pelo cliente:** {row['DEFEITO RELATADO']}")

                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button("✅ ACEITAR E PREENCHER O.S", key=f"aceitar_{idx}", use_container_width=True, type="primary"):
                                # Marca como aceita na planilha
                                df_sol.loc[idx, "STATUS"] = "aceita"
                                try:
                                    conn.update(worksheet=WORKSHEET_SOLICITACOES, data=df_sol)
                                except Exception as e:
                                    st.error(f"Erro ao atualizar status: {e}")
                                    st.stop()

                                # Pré-preenche campos da tela REGISTRAR O.S
                                st.session_state["placa"] = str(row["PLACA"]).strip().upper()
                                st.session_state["prop"] = str(row["NOME"]).strip()
                                st.session_state["diag"] = f"[Relato do cliente via formulário] {row['DEFEITO RELATADO']}"

                                # Redireciona para a tela de registro
                                st.session_state["forcar_menu"] = "REGISTRAR O.S"
                                st.toast("Solicitação aceita. Complete os dados do veículo em REGISTRAR O.S.")
                                st.rerun()

                        with col_b:
                            if st.button("❌ RECUSAR", key=f"recusar_{idx}", use_container_width=True):
                                df_sol.loc[idx, "STATUS"] = "recusada"
                                try:
                                    conn.update(worksheet=WORKSHEET_SOLICITACOES, data=df_sol)
                                    st.toast("Solicitação recusada.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao atualizar status: {e}")

            st.markdown("---")
            with st.expander("📜 Ver histórico completo de solicitações (aceitas/recusadas)"):
                st.dataframe(df_sol, use_container_width=True, hide_index=True)

    # -----------------------------------------------------------------------
    # TELA: SOBRE
    # -----------------------------------------------------------------------
    elif escolha == "SOBRE O APP":
        st.subheader("📱 Sobre o SGMA")
        st.markdown(f"""
        **Desenvolvedor:** Jonas Costa  
        **Versão:** {APP_VERSAO} - Beta

        O **SGMA** centraliza o registro de ordens de serviço, controle financeiro e histórico de atendimentos da sua oficina em um único lugar.

        Utiliza **Python**, **Streamlit** e integração em tempo real com **Google Sheets** para garantir dados sempre acessíveis, seguros e fáceis de analisar. Desenvolvido com foco em usabilidade, eficiência e escalabilidade — em constante evolução.

        Sugestões e críticas: [WhatsApp](https://wa.me/5521987360343) 📞
        """)

    st.sidebar.markdown("---")
    st.sidebar.caption(f"SGM Automotiva v{APP_VERSAO} · BETA 🚀")