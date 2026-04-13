# 🏆 Liga de Desempenho

Bem-vindo à **Liga de Desempenho**, um aplicativo web gamificado focado na educação, disciplina e incentivo de crianças e jovens atletas. 

O sistema transforma a rotina da casa e os deveres escolares/esportivos em um verdadeiro campeonato de futebol. Os pais assumem o papel da **Comissão Técnica** (gerenciando contratos, aplicando multas e dando bônus), enquanto os filhos entram no **Vestiário** para acompanhar seu Score, conquistar Badges, juntar dinheiro no Cofre e resgatar prêmios reais!

---

## 🎮 A Dinâmica do Jogo

O jogo funciona em ciclos mensais chamados de **Temporadas**. Durante a temporada, o atleta ganha ou perde "dinheiro virtual" com base no seu comportamento.

### 1. A Regra do Jogo (Faltas e Golaços)
* **🔴 Faltas (Multas):** Quando o atleta não cumpre um dever (ex: "Não fazer a lição" ou "Deixar a toalha no chão"), a Comissão Técnica aplica uma multa. Isso diminui o saldo do mês e aumenta a barra de "Tolerância de Faltas".
* **⭐ Bônus (Golaços):** Quando o atleta faz algo positivo (ex: "Ajudou a lavar a louça" ou "Fez gol no jogo"), ele ganha um bônus. 
* **A Mecânica do Perdão:** Os bônus não apenas aumentam o saldo de dinheiro, mas também **diminuem a barra de Faltas**. Se a criança errou, ela tem a chance de "limpar seu nome" ajudando nas tarefas de casa!

### 2. O Limite de Faltas e o Cartão Vermelho
Cada contrato possui um **Limite de Faltas** (ex: R$ 5,00). 
Se a barra de multas do atleta ultrapassar esse limite no mês, ele é bloqueado e **não pode subir de divisão**, mesmo que tenha muito dinheiro.
* **Cartão Vermelho:** Infrações gravíssimas (como "Desobedecer aos pais / Mentir") geram um Cartão Vermelho automático. Isso causa o **rebaixamento imediato** do atleta no fim da temporada, independente do saldo.

### 3. Fim da Temporada e o Cofre (Banco)
No final do mês, a Comissão Técnica clica em **"Encerrar Temporada"**. Nesse momento a mágica acontece:
1. Todo o "Saldo da Temporada" vira dinheiro real e é transferido para o **Cofre (Banco)** do atleta.
2. O sistema calcula se o atleta tem saldo suficiente para **Subir de Divisão**, se vai se **Manter** ou se será **Rebaixado**.
3. O histórico do mês é limpo, e uma nova temporada se inicia com o placar zerado.
4. O atleta recebe uma notificação no app dele com uma "Caixa Surpresa" para descobrir seu destino e a nova divisão!

---

## 🎖️ Sistema de Conquistas (Badges)

O aplicativo conta com um "Robô Olheiro" que analisa o histórico do atleta durante a temporada e distribui **Selos de Conquista** automáticos que ficam estampados no card do jogador:

* ⚽ **Artilheiro:** Concedido se o atleta receber bônus por gols no jogo/treino.
* 🧹 **Ajudante:** Concedido ao acumular 3 ou mais bônus de ajuda em casa (louça, lixo, limpeza, etc).
* 📚 **Estudioso:** Concedido ao focar nos estudos (bônus de lição, leitura, elogios na escola).
* 🛡️ **Intacto:** O selo de honra máxima. Exige participação ativa (pelo menos 3 lançamentos) e **ZERO multas** na temporada.

*(Nota: Os badges são resetados a cada nova temporada, incentivando a constância).*

---

## 🏦 A Economia: Temporada vs. Cofre

O aplicativo separa inteligentemente o dinheiro do mês atual e a poupança a longo prazo.

* **O Saldo da Temporada:** Fica flutuando (sobe e desce com faltas e bônus) e serve APENAS para definir se o garoto sobe ou cai de divisão no fim do mês.
* **O Cofre (Banco):** É o dinheiro blindado. É a soma de todas as temporadas passadas. Os prêmios finais (ex: "Chuteira Nova", "Jogo de Videogame") **só podem ser comprados usando o dinheiro do Banco**.
* **Depósitos Avulsos:** A comissão técnica pode fazer depósitos diretos no Cofre (ex: Mesada do avô, dinheiro de aniversário) sem interferir na pontuação do campeonato.

---

## 👔 O Painel da Comissão Técnica (Pais)

Acesso restrito por senha onde os pais gerenciam a família:
* **⚖️ Lançamentos:** Aplicação de Faltas, Golaços, Depósitos no Banco, Resgate de Prêmios e encerramento de temporada.
* **📝 Regras e Bônus:** Controle total sobre o valor das multas e recompensas. Os pais podem criar e editar regras à vontade.
* **⚙️ Elenco:** Contratação de novos atletas, edição de contratos (Piso, Aumento, Teto e Limite de Faltas) e definição do grande objetivo (Prêmio).
* **📊 Raio-X (Analytics):** Gráficos automatizados mostrando quais as faltas mais cometidas e os bônus mais frequentes, ajudando os pais a focarem na educação exata do que precisa ser melhorado.
* **🔗 Convite por WhatsApp:** Geração de um "Link Mágico" enviado pelo WhatsApp que loga a criança direto no vestiário usando apenas um PIN de 4 dígitos.

---

## 🏗️ A Matemática do Campeonato (Modo de Estreia)

Na hora de escalar (cadastrar) um atleta, os pais definem a matemática da liga baseada em 3 pilares: **Piso, Aumento e Teto**. O sistema monta automaticamente as Divisões (Pedras Preciosas: Ouro, Diamante, Esmeralda, etc.).

**A Temporada Zero:**
Ao cadastrar, os pais podem escolher a opção "Iniciar na Temporada Zero". O atleta nasce no jogo com o status **"Em Avaliação 🕵️‍♂️"** e saldo R$ 0,00. Durante o primeiro mês, ele será testado. No dia do encerramento, o sistema cruza o dinheiro que ele conseguiu juntar com a matemática (Piso/Teto) e diz automaticamente em qual Divisão ele merece estrear oficialmente!

---

## 💻 Tecnologias Utilizadas

* **Frontend / UI:** [Streamlit](https://streamlit.io/) (com injeção de CSS responsivo para Mobile e visual Flexbox).
* **Backend / Linguagem:** Python 3.
* **Banco de Dados:** PostgreSQL (gerenciado via SQLAlchemy `text` queries e `st.connection`).
* **Avatares:** API do [DiceBear](https://dicebear.com/).
* **Segurança:** Senhas e PINs dos atletas hasheados em SHA-256. Imagens auto-cropadas e convertidas para Base64.

## 🚀 Como Executar o Projeto

1. Clone este repositório.
2. Instale as dependências: `pip install streamlit pandas sqlalchemy psycopg2-binary pillow`
3. Configure os `secrets.toml` do Streamlit com a sua string de conexão do PostgreSQL.
4. Rode o aplicativo: `streamlit run app.py`

*Nota: O acesso de Super Administrador (Modo GOD) está atrelado ao e-mail configurado na variável `SUPER_ADMIN` no topo do código.*
