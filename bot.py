import discord
import os
from discord.ext import commands
from dotenv import load_dotenv


intents = discord.Intents.all()
intents.reactions = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Falta adicionar uma persistencia para items e queues.
items = {}  # Dicionário para armazenar os itens
queues = {}  # Fila de distribuição para cada item


@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')


@bot.command()
async def additem(ctx, channel: discord.TextChannel, name: str, description: str, image_url: str, category: str):
    """Adiciona um novo item e posta a mensagem no canal especificado."""
    embed = discord.Embed(title=name, description=description, color=discord.Color.blue())
    embed.set_image(url=image_url)
    embed.set_footer(text=f'Categoria: {category}')

    message = await channel.send(embed=embed)
    await message.add_reaction("✅")  # Reação para selecionar o item

    items[message.id] = {
        "name": name,
        "category": category,
        "queue": []  # Lista de espera para o item
    }

    # Envia a confirmação abaixo do comando no mesmo canal
    await ctx.send(f'✅ {ctx.author.mention}, o item **"{name}"** foi adicionado com sucesso em {channel.mention}!')

@bot.event
async def on_reaction_add(reaction, user):
    """Adiciona o membro à fila se ele tiver o cargo correto."""
    if user.bot:
        return

    message_id = reaction.message.id
    if message_id in items:
        item = items[message_id]
        member = reaction.message.guild.get_member(user.id)

        # Verifica se o membro tem um dos roles necessários
        allowed_roles = [role.name for role in member.roles]
        if item["category"] in allowed_roles:
            if user.id not in item["queue"]:
                item["queue"].append(user.id)
                await user.send(f'Você entrou na fila para {item["name"]}!')
            else:
                await user.send('Você já está na fila para esse item.')
        else:
            await user.send('Você não pode escolher este item, pois não tem o cargo correspondente!')
            await reaction.message.remove_reaction(reaction.emoji, user)


@bot.command()
async def markreceived(ctx, member: discord.Member, item_name: str):
    """Remove o membro da fila de um item após recebê-lo."""
    for message_id, item in items.items():
        if item["name"] == item_name:
            if member.id in item["queue"]:
                item["queue"].remove(member.id)
                await ctx.send(f'{member.mention} recebeu **{item_name}** e foi removido da fila!')
                return
    await ctx.send('Item não encontrado ou usuário não estava na fila.')

@bot.command()
async def ping(ctx):
    await ctx.send("Pong! 🏓")

# Carregar as variáveis do .env
load_dotenv()

# Obter o token
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

if DISCORD_TOKEN is None:
    raise ValueError("🚨 ERRO: O token do Discord não foi encontrado! Verifique seu arquivo .env.")


bot.run(DISCORD_TOKEN)
