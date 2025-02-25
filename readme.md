# Discord Item Bot

Um bot para Discord que permite aos membros escolher itens (armas e armaduras) com base nos seus cargos e gerencia a distribuição de forma justa.

## 🚀 Recursos

- Adiciona itens ao servidor com nome, descrição, imagem e categoria.
- Membros podem demonstrar interesse nos itens reagindo à mensagem.
- Apenas membros com cargos correspondentes podem escolher certos itens.
- Um sistema de fila garante que todos recebam pelo menos um item antes de repetirem.
- Administradores podem marcar quando um membro recebe um item, removendo-o da fila automaticamente.

---

## 📋 Instalação

### 1️⃣ Clonar o Repositório

```bash
git clone https://github.com/seu-usuario/seu-repositorio.git
cd seu-repositorio
```

### 2️⃣ Criar e Ativar um Ambiente Virtual (opcional, mas recomendado)

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate  # Windows
```

### 3️⃣ Instalar Dependências

```bash
pip install -r requirements.txt
```

### 4️⃣ Criar o Arquivo `.env`

Crie um arquivo chamado `.env` na pasta raiz do projeto e adicione:

```ini
DISCORD_TOKEN=seu_token_aqui
```

> 🔥 **Importante:** Nunca compartilhe seu token do Discord!

---

## ▶️ Como Executar o Bot

Execute o seguinte comando:

```bash
python bot.py
```

Se estiver usando ambiente virtual:

```bash
venv\Scripts\python bot.py  # Windows
source venv/bin/python bot.py  # Linux/macOS
```

O terminal deve exibir:

```
Bot conectado como NomeDoBot
```

---

## 🛠️ Comandos do Bot

### ✅ Adicionar um Item

```bash
!additem #canal "Nome do Item" "Descrição do Item" "URL_da_Imagem" "Categoria"
```

**Exemplo:**

```bash
!additem #boss-drops "Espada Lendária" "Uma espada forjada nas chamas da guerra." "https://exemplo.com/espada.png" "Espadão"
```

O bot responderá confirmando a adição do item e postará a mensagem no canal escolhido.

### 📌 Marcar que um Usuário Recebeu um Item

```bash
!markreceived @usuário "Nome do Item"
```

**Exemplo:**

```bash
!markreceived @Jogador "Espada Lendária"
```

Isso remove o usuário da fila de espera para o item.

---

## 🛠️ Problemas?

Caso tenha problemas ou dúvidas, abra uma issue no repositório ou entre em contato. 😊

