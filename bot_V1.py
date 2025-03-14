import discord
import os
import logging
import json
import asyncio
from discord.ext import commands
from dotenv import load_dotenv

# 📌 Configuração dos Intents
intents = discord.Intents.all()
intents.reactions = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# 📌 Arquivos de persistência
ITEMS_FILE = "database/items.json"
BACKUP_FILE = "database/backup.json"

# 📌 Dicionário para armazenar os itens e filas
items = {}

# Logging
logger = logging.getLogger(__name__)

# 📌 Canal onde os itens são postados
canal_boss_drops = "🤝boss-drops"


# 📌 Função para salvar o backup no arquivo JSON
def salvar_backup():
    """Salva os itens e filas no arquivo backup.json."""
    try:
        os.makedirs("database", exist_ok=True)  # Garante que a pasta database existe
        with open(BACKUP_FILE, "w", encoding="utf-8") as file:
            json.dump(items, file, indent=4, ensure_ascii=False)
        print("✅ Backup atualizado com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao salvar backup: {e}")


# 📌 Função para carregar os dados do backup
def carregar_backup():
    """Carrega os itens e filas do arquivo backup.json."""
    global items

    if not os.path.exists(BACKUP_FILE):
        print("⚠️ Arquivo de backup não encontrado. Criando um novo...")
        salvar_backup()
        return

    try:
        with open(BACKUP_FILE, "r", encoding="utf-8") as file:
            items = json.load(file)
        print(f"✅ Backup carregado com sucesso! {len(items)} itens restaurados.")
    except Exception as e:
        print(f"❌ Erro ao carregar backup: {e}")


# 📌 Evento que ocorre quando o bot está pronto
@bot.event
async def on_ready():
    """Carrega os dados do backup e verifica reações antigas."""
    print(f'Bot conectado como {bot.user}')
    carregar_backup()
    await check_reactions(None)  # Verifica se há reações inválidas
    logger.info('on_ready: Finished')


# 📌 Comando para carregar todos os itens do JSON para o canal de drops
@bot.command()
async def load_all_items(ctx, channel: discord.TextChannel):
    """Carrega todos os itens do arquivo items.json e os adiciona ao canal especificado."""

    if not os.path.exists(ITEMS_FILE):
        await ctx.send("❌ Arquivo `items.json` não encontrado! Certifique-se de que ele está na pasta `database`.")
        return

    try:
        with open(ITEMS_FILE, "r", encoding="utf-8") as file:
            items_list = json.load(file)

        if not items_list:
            await ctx.send("❌ Nenhum item encontrado no arquivo `items.json`.")
            return

        for item in items_list:
            name = item["name"]
            description = item["description"]
            image_url = item["image_url"]
            categories = item["categories"]

            embed = discord.Embed(title=name, description=description, color=discord.Color.blue())
            embed.set_image(url=image_url)
            embed.set_footer(text=f'Categorias: {", ".join(categories)}')

            message = await channel.send(embed=embed)
            await message.add_reaction("✅")

            # Adicionar ao dicionário do bot
            items[str(message.id)] = {
                "name": name,
                "category": categories,
                "queue": []
            }

        # Salvar backup após adicionar os itens
        salvar_backup()

        await ctx.send(f"✅ Todos os itens foram carregados e adicionados ao canal {channel.mention}!")

    except Exception as e:
        await ctx.send(f"❌ Erro ao carregar itens: {str(e)}")
        print(f"Erro ao carregar JSON: {str(e)}")


# 📌 Evento para adicionar um usuário à fila ao reagir
@bot.event
async def on_reaction_add(reaction, user):
    """Adiciona o membro à fila se ele tiver a role correta e salva no backup."""
    if user.bot:
        return

    message_id = str(reaction.message.id)
    if message_id in items:
        item = items[message_id]
        member = reaction.message.guild.get_member(user.id)

        if any(role.name in item["category"] for role in member.roles):
            if user.id not in item["queue"]:
                item["queue"].append(user.id)
                await user.send(f'✅ Você entrou na fila para {item["name"]}!')
                salvar_backup()
        else:
            await user.send(f'❌ Você não pode escolher este item ({item["name"]}), pois não tem a role necessária!')
            await reaction.message.remove_reaction(reaction.emoji, user)


# 📌 Evento para remover um usuário da fila ao remover a reação
@bot.event
async def on_reaction_remove(reaction, user):
    """Remove o membro da fila caso ele retire a reação e salva no backup."""
    if user.bot:
        return

    message_id = str(reaction.message.id)
    if message_id in items:
        item = items[message_id]
        if user.id in item["queue"]:
            item["queue"].remove(user.id)
            await user.send(f'⚠️ Você foi removido da fila para {item["name"]}.')
            salvar_backup()


# 📌 Comando para marcar que um membro recebeu um item
@bot.command()
async def markreceived(ctx, member: discord.Member, item_name: str):
    """Remove o membro da fila de um item após recebê-lo e salva no backup."""
    for message_id, item in items.items():
        if item["name"] == item_name:
            if member.id in item["queue"]:
                item["queue"].remove(member.id)
                salvar_backup()
                await ctx.send(f'{member.mention} recebeu **{item_name}** e foi removido da fila!')
                return
    await ctx.send('Item não encontrado ou usuário não estava na fila.')


# 📌 Função para verificar reações antigas ao iniciar
@bot.command()
async def check_reactions(ctx):
    """Verifica se há reações inválidas no canal de drops e atualiza as filas."""
    await bot.wait_until_ready()
    guild = bot.guilds[0]
    drops_channel = discord.utils.get(guild.text_channels, name=canal_boss_drops)

    if not drops_channel:
        print("🚨 Canal de drops não encontrado!")
        return

    async for message in drops_channel.history(limit=100):
        message_id = str(message.id)
        if message_id in items:
            item = items[message_id]
            reacted_users = set()

            for reaction in message.reactions:
                async for user in reaction.users():
                    if user.bot:
                        continue

                    member = guild.get_member(user.id)
                    if not member:
                        continue

                    if any(role.name in item["category"] for role in member.roles):
                        reacted_users.add(user.id)
                        if user.id not in item["queue"]:
                            item["queue"].append(user.id)
                    else:
                        await message.remove_reaction(reaction.emoji, user)
                        await member.send(f'❌ Você não pode escolher este item ({item["name"]}), pois não tem a role necessária!')

            users_to_remove = [uid for uid in item["queue"] if uid not in reacted_users]
            for user_id in users_to_remove:
                item["queue"].remove(user_id)
                member = guild.get_member(user_id)
                if member:
                    try:
                        await member.send(
                            f'⚠️ Você foi removido da fila para {item["name"]} porque retirou a reação enquanto o bot estava offline.')
                    except discord.Forbidden:
                        print(f"⚠️ Não foi possível enviar DM para {member}")

    salvar_backup()
    print("✅ Verificação de reações concluída!")


# 📌 Evento para iniciar o bot
@bot.event
async def setup_hook():
    bot.loop.create_task(check_reactions(None))


# Carregar variáveis do .env
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

if DISCORD_TOKEN is None:
    raise ValueError("🚨 ERRO: O token do Discord não foi encontrado! Verifique seu arquivo .env.")

bot.run(DISCORD_TOKEN)
