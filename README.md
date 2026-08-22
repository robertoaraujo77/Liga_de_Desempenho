# 🏆 Liga de Desempenho

## 💡 A Ideia

**Liga de Desempenho** é um aplicativo web que transforma a rotina de casa, a disciplina e o
desempenho esportivo de uma criança ou jovem atleta em um verdadeiro **campeonato de futebol**.

A ideia por trás do projeto é simples: crianças costumam se engajar muito mais com um sistema
de jogo (pontos, divisões, conquistas, dinheiro pra guardar) do que com pedidos e cobranças
repetidas dos pais. Em vez de "arrumar o quarto" ser só mais uma obrigação, ela vira parte de
uma temporada de futebol onde o próprio atleta pode subir de divisão, ganhar troféus e juntar
dinheiro de verdade para um prêmio que ele escolheu.

Os pais (ou treinadores) assumem o papel da **Comissão Técnica**: definem as regras do jogo,
aplicam multas quando algo não é cumprido e dão bônus quando o atleta faz por merecer. Os
filhos entram no **Vestiário**: acompanham seu Score, badges, o cofre e a lista de prêmios que
estão tentando conquistar.

O app foi feito pensando em uso real dentro de uma família — não é um produto genérico, é uma
ferramenta sob medida para o dia a dia doméstico, com foco em celular (funciona como PWA,
"instalável" na tela inicial do telefone).

---

## 🎮 Como o Jogo Funciona

### 1. Temporadas, Faltas e Bônus

O jogo funciona em ciclos (**Temporadas**, normalmente mensais). Durante a temporada, o atleta
ganha ou perde "dinheiro virtual" com base no seu comportamento:

- **🔴 Faltas (Multas):** quando o atleta não cumpre um dever (ex: "Não fazer a lição",
  "Deixar a toalha no chão"), a Comissão Técnica aplica uma multa. Isso diminui o saldo do mês
  e aumenta a barra de "Tolerância de Faltas".
- **⭐ Bônus (Golaços):** quando o atleta faz algo positivo (ex: "Ajudou a lavar a louça",
  "Fez gol no jogo"), ele ganha um bônus.
- **A Mecânica do Perdão:** os bônus não só aumentam o saldo — eles também **diminuem a barra
  de Faltas**. Se a criança errou, ela tem a chance de "limpar seu nome" fazendo algo de bom
  depois.
- **Bônus Extra:** um bônus avulso, digitado na hora pela Comissão, para situações que não têm
  uma regra cadastrada.
- **Depósito Extra:** dinheiro que não interfere na pontuação da temporada — vai direto pro
  Cofre (ex: mesada, presente de aniversário, dinheiro dos avós).

### 2. Limite de Faltas e Cartão Vermelho

Cada atleta tem um **Limite de Faltas** (ex: R$ 20,00) — se a barra de multas do mês ultrapassar
esse valor, o atleta fica bloqueado e **não sobe de divisão** naquele mês, mesmo com saldo
positivo.

Além disso, algumas faltas podem ser marcadas como **🟥 Cartão Vermelho** — infrações mais
graves (ex: "Desobedecer aos pais"). Aplicar uma falta desse tipo garante o **rebaixamento
automático** do atleta no fim da temporada, **independente do saldo financeiro**. Essa marcação
é feita por atributo, não pelo texto da regra — então renomear a descrição de uma falta nunca
quebra esse comportamento, e qualquer regra nova ou existente pode virar Cartão Vermelho
marcando uma caixinha na hora de criar/editar a falta.

### 3. Fim de Temporada

A temporada pode ser encerrada de duas formas:

- **Manual:** a Comissão Técnica clica em "Autorizar Fim da Temporada".
- **🔁 Automático (opcional):** cada atleta pode ter um fechamento automático configurado
  ("fechar sozinho a cada X dias"). O app confere isso sempre que é aberto e fecha a temporada
  sozinho quando o prazo vence — sem precisar ninguém lembrar de clicar em nada.

Quando a temporada fecha:
1. Todo o **Saldo da Temporada** vira dinheiro real e é transferido pro **Cofre (Banco)**.
2. O sistema calcula se o atleta **Sobe**, **Mantém** ou é **Rebaixado** de divisão (considerando
   saldo, limite de faltas e Cartão Vermelho).
3. O histórico do mês é limpo e uma nova temporada começa zerada.
4. O atleta recebe uma notificação com uma "Caixa Surpresa" pra descobrir seu resultado.

---

## 🎖️ Sistema de Conquistas (Badges)

O app analisa o histórico da temporada e distribui selos automáticos, exibidos no card do
jogador:

| Badge | Critério |
|---|---|
| ⚽ **Artilheiro** | Recebeu ao menos 1 bônus relacionado a gol |
| 🧹 **Ajudante** | 3 ou mais bônus de tarefas de casa (louça, lixo, limpeza, cama) |
| 📚 **Estudioso** | 2 ou mais bônus relacionados a estudos (livro, escola, lição, dever) |
| 🔥 **Atleta Focado** | 2 ou mais bônus relacionados a treino/desafio |
| 🛡️ **Intacto** | Zero multas na temporada, com pelo menos 3 lançamentos no histórico |

*Os badges são calculados por temporada — resetam a cada novo ciclo, incentivando a
constância.*

---

## 🔥 Streak — Dias Sem Faltas

O app acompanha há quantos dias o atleta não recebe nenhuma falta, exibindo em destaque na
visão do atleta (ex: "🔥 12 dias sem faltas!"). Esse contador **não reseta** ao fechar a
temporada — ele é zerado apenas quando uma nova falta é aplicada, incentivando constância de
verdade e não só dentro de um mês.

---

## 🎯 Lista de Desejos (Metas do Cofre)

Cada atleta pode ter **vários prêmios cadastrados ao mesmo tempo** (ex: "Chuteira Nova — R$
80", "Videogame — R$ 300"), cada um com sua própria barra de progresso calculada em cima do
dinheiro guardado no Cofre. A Comissão Técnica pode comprar qualquer item da lista assim que o
Cofre tiver saldo suficiente — o valor é debitado e o item sai da lista.

---

## 🏦 A Economia: Temporada vs. Cofre

- **Saldo da Temporada:** sobe e desce com faltas e bônus. Serve apenas para decidir se o
  atleta sobe, mantém ou desce de divisão no fim do mês.
- **Cofre (Banco):** dinheiro "blindado", soma de todas as temporadas já fechadas mais
  depósitos avulsos. É de onde saem as compras da Lista de Desejos.

---

## 📊 Acompanhamento e Relatórios

- **Resumo Semanal:** cards com total de faltas, bônus e saldo líquido dos últimos 7 dias, pra
  não precisar esperar o fechamento do mês pra saber como está indo.
- **Desempenho Diário:** gráfico dia a dia mostrando ganhos (verde) e perdas (vermelho) da
  temporada atual, em ordem cronológica real.
- **Evolução entre Temporadas:** na Sala de Troféus, gráficos de linha (evolução de divisão) e
  de barras (dinheiro ganho por temporada), disponíveis a partir da 2ª temporada fechada.
- **Raio-X (Comissão):** analytics de quais faltas e bônus mais aparecem no histórico, ajudando
  os pais a identificar padrões de comportamento.

---

## 👔 O Painel da Comissão Técnica (Pais)

Área restrita por senha, dividida em abas:

- **⚖️ Lançamentos:** aplicar Faltas, Golaços (bônus), Bônus Extra, Depósitos no Banco, efetuar
  compras da Lista de Desejos, excluir itens do extrato e encerrar a temporada.
- **📝 Regras e Bônus:** criar, editar e excluir faltas e bônus, incluindo marcar/desmarcar uma
  falta como Cartão Vermelho. Um botão permite recarregar o conjunto de regras padrão.
- **⚙️ Elenco:**
  - *Escalar:* cadastrar um novo atleta (nome, avatar/foto, PIN de acesso, matemática da liga,
    prêmio inicial, fechamento automático).
  - *Contrato:* editar qualquer dado do atleta (nome, avatar, PIN, valores financeiros, saldo do
    Cofre, fechamento automático) e gerenciar a Lista de Desejos.
  - *Demitir:* remover um atleta e todos os seus dados.
  - *Convite:* gerar um "Link Mágico" para compartilhar por WhatsApp, que loga a criança direto
    no Vestiário digitando apenas um PIN de 4 dígitos.
- **📊 Raio-X:** gráficos com as faltas e bônus mais recorrentes do atleta.

### Modo GOD (Super Administrador)

Login com o e-mail configurado no **Secret `SUPER_ADMIN`** do Streamlit dá acesso a um painel
especial na barra lateral, permitindo:
- Acessar/gerenciar os dados de qualquer família cadastrada no sistema (impersonar).
- Recarregar o conjunto de regras padrão para a família selecionada.
- Apagar uma família inteira (com confirmação escrita), removendo todos os dados relacionados.

---

## 🏗️ A Matemática do Campeonato

Ao cadastrar um atleta, a Comissão define 3 pilares: **Piso** (base inicial), **Aumento**
(incremento entre divisões) e **Teto Máximo**. O sistema monta automaticamente as divisões,
nomeadas com pedras/minérios (Ouro, Diamante, Esmeralda, etc.) — quanto **menor** o número da
divisão, **melhor** a colocação (1ª Divisão é a mais alta, como no futebol brasileiro).

**Temporada Zero:** ao cadastrar, é possível marcar "Iniciar na Temporada Zero" — o atleta
começa como **"Em Avaliação 🕵️‍♂️"** com saldo R$ 0,00. No fim do primeiro mês, o sistema cruza
o dinheiro conquistado com a matemática configurada (Piso/Teto) e classifica automaticamente o
atleta na divisão correspondente para estrear oficialmente.

**Limite de Faltas Dinâmico:** a cada mudança de divisão, o Limite de Faltas é recalculado
automaticamente como 20% da nova Base daquela divisão.

---

## 💻 Tecnologias Utilizadas

- **Frontend / UI:** [Streamlit](https://streamlit.io/), com CSS injetado para visual responsivo
  em mobile e tema Dark Mode fixo (`.streamlit/config.toml`).
- **Backend / Linguagem:** Python 3.
- **Banco de Dados:** PostgreSQL (hospedado no [Neon](https://neon.tech)), acessado via
  `st.connection("postgresql")` + SQLAlchemy (`text()` queries).
- **Gráficos:** [Altair](https://altair-viz.github.io/) para os gráficos de desempenho diário e
  evolução entre temporadas (cor por resultado, eixo temporal real).
- **Avatares:** API do [DiceBear](https://dicebear.com/), com opção de foto própria
  (auto-cropada e convertida para Base64).
- **Segurança:** senhas e PINs hasheados em SHA-256.
- **PWA:** `manifest.json` + `sw.js` + `index.html`, permitindo instalar o app na tela inicial do
  celular como se fosse nativo.

---

## 🚀 Como Executar o Projeto Localmente

1. Clone este repositório:
   ```bash
   git clone https://github.com/robertoaraujo77/Liga_de_Desempenho.git
   cd Liga_de_Desempenho
   ```
2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure o banco: crie um arquivo `.streamlit/secrets.toml` com a string de conexão do seu
   PostgreSQL (Neon ou outro), no formato exigido por `st.connection("postgresql")`.
4. Rode o aplicativo:
   ```bash
   streamlit run app.py
   ```

O banco é criado e migrado automaticamente na primeira execução (função `init_db()`) — não é
necessário rodar nenhum script de setup manual.

> **Nota:** o acesso de Super Administrador (Modo GOD) está atrelado ao e-mail configurado no
> **Secret `SUPER_ADMIN`** (não fica hardcoded no código, já que o repositório é público). Para
> rodar localmente, adicione a linha `SUPER_ADMIN = "seu-email@exemplo.com"` no seu
> `.streamlit/secrets.toml`, junto com a string de conexão do banco. Em produção, configure o
> mesmo em Streamlit Cloud > Manage app > Settings > Secrets.

---

## ☁️ Deploy

O app roda em produção no **Streamlit Community Cloud**:
👉 https://ligadedesempenho.streamlit.app/

Qualquer push na branch `main` deste repositório dispara um redeploy automático. Não existe
ambiente de staging — toda alteração enviada para `main` vai direto para produção.

---

## 🗂️ Estrutura do Projeto

```
├── app.py                  # Toda a aplicação (backend + frontend + queries)
├── requirements.txt        # Dependências Python
├── .streamlit/
│   └── config.toml         # Tema visual (Dark Mode) e configuração do servidor
├── index.html              # Landing page do PWA (redireciona para o app no Streamlit Cloud)
├── sw.js                   # Service worker do PWA
├── static/
│   ├── manifest.json       # Manifesto do PWA
│   ├── icon-192.png
│   └── icon-512.png
├── CLAUDE.md                # Contexto do projeto para sessões do Claude Code
└── README.md                # Este arquivo
```

Mais detalhes técnicos de arquitetura, schema do banco e histórico de decisões estão no
[`CLAUDE.md`](./CLAUDE.md).
