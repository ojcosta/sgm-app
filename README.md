# 🚘 SGM Automotiva - Sistema de Gestão Mecânica

![Versão](https://img.shields.io/badge/vers%C3%A3o-9.2--Stable-blue)
![Python](https://img.shields.io/badge/Python-3.10%2B-green)
![Streamlit](https://img.shields.io/badge/Framework-Streamlit-red)
![Google Sheets](https://img.shields.io/badge/Banco%20de%20Dados-Google%20Sheets-yellow)

O **SGM Automotiva** é uma aplicação web desenvolvida para otimizar, centralizar e simplificar o fluxo de trabalho de oficinas mecânicas e garagens. O sistema une a agilidade de uma interface moderna em Python com a praticidade de um banco de dados em nuvem utilizando o Google Sheets.

---

## 🚀 Funcionalidades Principais

* **🔐 Portal de Acesso Restrito:** Sistema de autenticação integrado para operadores e mecânicos da oficina, garantindo a segurança dos dados.
* **📝 Registro Digital de OS:** Cadastro automatizado de Ordens de Serviço com cálculo dinâmico do próximo número de OS, validação de campos obrigatórios e feedback de salvamento em tempo real.
* **🔍 Inteligência de Negócio (BI):** Painel financeiro completo na aba de histórico que calcula automaticamente:
    * Faturamento Total da oficina.
    * Ticket Médio por atendimento.
    * Serviço mais frequente (Moda estatística).
* **📊 Filtros Avançados:** Busca rápida por Placa ou número de OS, além de filtragem segmentada por mecânico responsável.
* **🎨 Interface Customizada:** Visual limpo com tabela de dados formatada (moeda em R$ e datas em padrão PT-BR) e inclusão da identidade visual da oficina.

---

## 🛠️ Tecnologias Utilizadas

* **Linguagem:** Python
* **Interface Web:** [Streamlit](https://streamlit.io/)
* **Manipulação de Dados:** [Pandas](https://pandas.pydata.org/)
* **Banco de Dados:** [Google Sheets API](https://developers.google.com/sheets/api) (via `streamlit-gsheets`)

---

## 📦 Como Executar o Projeto Localmente

### 1. Clonar o Repositório
```bash
git clone [https://github.com/SEU_USUARIO/SGM-Automotiva.git](https://github.com/SEU_USUARIO/SGM-Automotiva.git)
cd SGM-Automotiva

2. Instalar as Dependências
Certifique-se de ter o Python instalado e execute:

Bash
pip install streamlit pandas streamlit-gsheets

3. Configurar as Chaves de Acesso (Secrets)
Crie uma pasta chamada .streamlit na raiz do projeto e, dentro dela, um arquivo secrets.toml. Adicione as credenciais de conexão do seu Google Sheets:

Ini, TOML
[connections.gsheets]
spreadsheet = "SUA_URL_DA_PLANILHA_DO_GOOGLE_SHEETS"

4. Rodar a Aplicação
Bash
streamlit run app.py
🧑‍💻 Desenvolvedor
Jonas Costa - Desenvolvimento Geral & Arquitetura de Software

💡 Dicas antes de postar no GitHub:
Ajuste os links: No comando git clone, mude SEU_USUARIO para o seu nome de usuário real do GitHub.

Badges: As primeiras linhas contêm "badges" (aqueles botões coloridos de versão, Python, etc.). Eles vão renderizar perfeitamente no GitHub, dando uma estética excelente ao projeto.

Segurança: Reforcei no arquivo de texto que a configuração de banco de dados deve ser feita via secrets.toml, o que mostra para quem estiver avaliando que você seguiu boas práticas de segurança da informação!
