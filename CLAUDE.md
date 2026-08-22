# CLAUDE.md — Contexto do Projeto Liga de Desempenho

Este arquivo dá contexto automático para o Claude Code sempre que ele abrir esta pasta.
Fale comigo (Claude) sempre em **Português Brasileiro**.

## 1. O que é o projeto

App web gamificado para incentivar disciplina/desempenho esportivo de crianças e atletas
(uso real: filho do dono do projeto, Davi Araujo). Pais/treinadores ("Comissão Técnica")
aplicam "Faltas" (multas) e "Bônus" no atleta. O desempenho do mês define a Divisão
(sistema de rebaixamento/acesso, tipo futebol) e o dinheiro que vai pro "Cofre".

## 2. Stack

- **Linguagem/Framework:** Python 3 + Streamlit
- **Arquitetura de arquivos (refatorado — antes era um único `app.py` de ~1470 linhas):**
  - `config.py` — constantes (PEDRAS, ESTILOS_AVATAR, CSS_APP, regras/bônus padrão) e
    `SUPER_ADMIN` (lido de `st.secrets`, não hardcoded — ver seção 7)
  - `logic.py` — funções puras (hash de senha, crop de imagem, cálculo de divisão/score/badges,
    renderização do card do atleta, popups)
  - `database.py` — toda a camada de banco: conexão (`conn`), `init_db()` e todas as funções de
    CRUD. Usa uma função interna `_usuario_ativo()` (lê `st.session_state` diretamente) no lugar
    do antigo global `USER_LOGADO` que existia quando tudo estava num arquivo só.
  - `app.py` — só o fluxo de telas/UI (login, abas, formulários), importando dos 3 módulos acima
    via `from config import *`, `from logic import *`, `from database import *`
- **Hospedagem:** Streamlit Community Cloud → https://ligadedesempenho.streamlit.app/
- **Banco:** PostgreSQL (Neon), via `st.connection("postgresql")` + SQLAlchemy `text()`
- **Tema:** Dark mode forçado via `.streamlit/config.toml`
- **PWA:** `static/manifest.json`, `sw.js`, `index.html` (landing/redirect hospedado no GitHub Pages)
- **Deploy:** git push na branch `main` → redeploy automático no Streamlit Cloud

## 3. Estrutura do banco (Postgres/Neon)

- `usuarios`: login dos pais (username, password SHA-256)
- `status`: perfil de cada atleta — nivel, base, saldo, faltas, aguardando_resgate, avatar,
  base_inicial, incremento, teto_maximo, titulos, limite_faltas, pin_jogador,
  meta_descricao/meta_valor (**legado, não usado mais na UI**, ver seção 5), poupanca,
  **data_cadastro, data_ultima_falta** (streak), **fechamento_automatico, dias_fechamento,
  data_inicio_temporada** (fechamento automático de temporada)
- `historico`: extrato (usuario, nome, data "DD/MM/YYYY HH:MM", infracao, desconto, tipo
  ['falta','bonus','compra','deposito'], **cartao_vermelho** bool)
- `trofeus`: divisão + dinheiro faturado ao fim de cada temporada
- `regras` / `bonus_regras`: catálogo dinâmico de faltas/bônus e seus valores.
  `regras` tem coluna **cartao_vermelho** (bool) — falta marcada assim causa rebaixamento
  automático no fim de temporada, independente do texto da descrição
- `notificacoes`: alertas pro atleta
- `metas`: **lista de desejos** (id, usuario, jogador, descricao, valor) — um atleta pode
  ter várias metas/prêmios, cada uma com sua barra de progresso e compra individual

## 4. Regras de negócio principais

- **Divisões:** calculadas a partir de Piso (base_inicial), Aumento (incremento) e Teto
  Máximo, usando nomes de pedras/minérios (`PEDRAS`). **Quanto menor o número da divisão,
  melhor** (1ª Divisão é a melhor, número mais alto é pior — como futebol brasileiro).
- **Falta:** desconta do saldo da temporada e aumenta a "barra de multas".
- **Bônus:** soma no saldo e **diminui** a barra de multas (mecânica do perdão).
- **Cartão Vermelho:** regras marcadas com `cartao_vermelho=True` causam rebaixamento
  garantido no fechamento de temporada, sem depender do texto da descrição da regra
  (isso foi um bug corrigido — ver seção 6).
- **Limite de faltas:** recalculado automaticamente como 20% da nova Base a cada
  subida/descida de divisão.
- **Fim de temporada:** saldo vira dinheiro de verdade no Cofre (poupança); o atleta
  aprova clicando em "Ver Resultado". Pode ser manual (botão da Comissão) ou
  **automático** (toggle por atleta, fecha sozinho a cada X dias — ver seção 5).

## 5. Funcionalidades adicionadas nesta parceria (além do código original em Gemini)

1. **Correção: Cartão Vermelho por flag, não por texto** — antes a detecção buscava a
   string "Cartão Vermelho" na descrição da falta; se o pai renomeasse a regra, o
   rebaixamento parava de funcionar silenciosamente. Agora é uma coluna booleana em
   `regras` e `historico` (denormalizada no momento do lançamento, então renomear
   depois não quebra o histórico já gravado).
2. **Correção: excluir um Bônus não devolvia a barra de faltas** — a "mecânica do
   perdão" reduzia as faltas ao aplicar um bônus, mas ao excluir esse lançamento só o
   saldo era revertido. Corrigido para reverter os dois.
3. **Streak (dias sem faltas)** — `data_ultima_falta` / `data_cadastro` em `status`,
   exibido como "🔥 X dias sem faltas!" na visão do atleta.
4. **Evolução entre temporadas** — gráficos (linha de divisão + barras de dinheiro) na
   Sala de Troféus, a partir de 2 temporadas fechadas.
5. **Lista de Desejos (múltiplas metas)** — substituiu o sistema de "meta única"
   (`meta_descricao`/`meta_valor` em `status`, que ficou **legado/não usado** na UI,
   mas os dados antigos foram migrados automaticamente pra tabela `metas` no `init_db()`).
6. **Resumo Semanal** — cards de Faltas/Bônus/Saldo Líquido dos últimos 7 dias.
7. **Fechamento Automático de Temporada (opcional)** — toggle por atleta
   ("fechar a cada X dias"), verificado a cada carregamento do app (não há cron real no
   Streamlit Cloud, então a checagem é "preguiçosa": só dispara quando alguém abre o app
   depois do prazo vencido).
8. **Melhorias visuais** — anel colorido no Score (verde/laranja/vermelho), cards de
   Saldo/Multas com fundo colorido, barra de tolerância com texto sobreposto, aba ativa
   destacada em verde, aviso 🟥 no dropdown de falta quando é Cartão Vermelho.
9. **Gráfico de Desempenho Diário reescrito com Altair** — o `st.bar_chart` nativo não
   diferenciava cor por ganho/perda e agrupava por texto da data (ordem alfabética, não
   cronológica — quebraria em faltas de meses diferentes). Trocado por gráfico Altair
   com cor verde/vermelho por dia e eixo temporal de verdade.
10. **Refatoração em múltiplos arquivos** — o `app.py` (que chegou a ~1470 linhas) foi separado
    em `config.py` / `logic.py` / `database.py` / `app.py`, sem alterar nenhuma lógica de
    negócio (só reorganização). Ver seção 2 para detalhes de cada módulo. Validado via
    checagem cruzada de que toda função/constante movida existe em exatamente um módulo novo e
    é usada corretamente, mais um "dry run" simulando a execução fora do Streamlit Cloud
    (não há ambiente de teste real disponível para este projeto).

## 6. Bugs encontrados e corrigidos (histórico)

- Ver itens 1 e 2 da seção 5.
- **Race condition na migração do banco:** o primeiro deploy quebrou porque duas sessões
  concorrentes tentaram rodar `ALTER TABLE ... ADD COLUMN` ao mesmo tempo. Trocado para
  `ADD COLUMN IF NOT EXISTS` (idempotente, sem race).
- **Bug introduzido e corrigido na mesma sessão:** ao montar HTML dos cards de
  Saldo/Multas, um `.replace('.', ',')` aplicado no bloco inteiro corrompia valores
  decimais do CSS (`rgba(40,167,69,0.15)` virava `0,15`, CSS inválido). Corrigido
  formatando só o valor monetário antes de montar o HTML.
- **Bug no fechamento automático:** se o atleta tivesse fechamento automático ativado e
  o pai clicasse em "Cancelar Fim de Temporada", a temporada reabria mas
  `data_inicio_temporada` não era resetada — no próximo carregamento o app fechava a
  temporada nomamente de novo, criando um loop. Corrigido resetando a data ao cancelar.

## 7. Pendências / coisas que o Roberto sabe e decidiu conscientemente

- O dossiê original do projeto (feito no Gemini) mencionava que **"Mentir para os pais"**
  também deveria gerar Cartão Vermelho, mas no código real só "Desobedecer aos pais"
  tinha esse efeito. Mantive o comportamento do código real (não mudei a regra do jogo
  sem pedido explícito) — dá pra ativar isso pela UI (checkbox na tela de editar falta).
- O dossiê também menciona `wa_numero`/`wa_apikey` (integração WhatsApp) e Supabase→Neon;
  **não implementamos nada de API do WhatsApp** (decisão explícita do Roberto).
- As colunas `meta_descricao`/`meta_valor` em `status` continuam no banco por segurança
  (não quebram nada), mas não são mais escritas nem lidas pela UI atual.
- **IMPORTANTE — ação manual necessária no Streamlit Cloud:** `SUPER_ADMIN` foi movido de
  hardcoded no código para `st.secrets` (o repositório é público, e antes disso o e-mail do
  Modo GOD ficava visível pra qualquer um no GitHub). Isso significa que o Roberto **precisa**
  adicionar `SUPER_ADMIN = "robertojr1990@gmail.com"` em Manage app > Settings > Secrets no
  Streamlit Cloud (junto da string de conexão do banco) — sem isso, o Modo GOD fica
  inacessível (o resto do app continua funcionando normalmente, é uma falha segura). Se uma
  sessão futura do Claude notar o Modo GOD "sumido", checar isso primeiro antes de mexer em
  qualquer lógica de login.

## 8. Convenções de código a manter

- Datas em `historico`/`status` são salvas como `TEXT` no formato `"%d/%m/%Y"` ou
  `"%d/%m/%Y %H:%M"` — sempre usar `pd.to_datetime(..., format=...)` ao invés de
  comparar/ordenar como texto puro (já causou um bug real, ver item de gráfico acima).
- Migrações de schema em `init_db()` devem ser sempre `ADD COLUMN IF NOT EXISTS`
  (idempotentes), nunca `SELECT information_schema` + `IF NOT IN` (tem race condition).
- `get_status()` (em `database.py`) retorna uma tupla posicional grande — ao adicionar campos
  novos, **sempre no final da tupla** pra não quebrar os acessos por índice (`d_edit[N]`)
  espalhados pelo `app.py`.
- Ao renomear um atleta (`edit_jogador`, em `database.py`), lembrar de propagar o nome novo em
  TODAS as tabelas relacionadas: `historico`, `trofeus`, `notificacoes`, `metas`.
- Sempre rodar `python3 -m py_compile app.py config.py logic.py database.py` depois de qualquer
  edição, antes de commitar.
- Novas funções de banco vão em `database.py`; use `_usuario_ativo()` (não um global) para saber
  qual conta de pai está ativa — essa função já lida com o Modo GOD (impersonate) internamente.
- Novas constantes/dados padrão vão em `config.py`. Novas funções puras (sem tocar banco) vão em
  `logic.py`. O `app.py` deve conter só fluxo de tela — se uma função nova não depende de
  `st.session_state` nem de Streamlit para além de renderizar algo simples, ela provavelmente
  pertence a `logic.py`, não a `app.py`.

## 9. Deploy / Git

- Repositório: `github.com/robertoaraujo77/Liga_de_Desempenho`, branch `main`
- Push para `main` → redeploy automático no Streamlit Cloud (leva alguns segundos)
- Não há ambiente de staging — toda alteração vai direto pra produção
