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


canal_persistencia_bot = "bot-data"

@bot.event
async def on_ready():
    """Carrega os dados do canal de persistência ao iniciar."""
    print(f'Bot conectado como {bot.user}')

    log_channel = discord.utils.get(bot.get_all_channels(), name=canal_persistencia_bot)
    if not log_channel:
        print("Canal de persistência não encontrado!")
        return

    async for message in log_channel.history(limit=100):
        # Ignora mensagens do tipo 'pins_add' (fixação de mensagens) ou outros tipos que não sejam comuns
        if message.type == discord.MessageType.pins_add:
            continue  # Ignora a mensagem e passa para a próxima

        print("message")
        print(message)
        parts = message.content.split(" | ")
        print("parts")
        print(parts)

        message_id = int(parts[0])
        name = parts[1]
        categories = parts[2].split(", ")
        queue = eval(parts[3])  # Converte a string da fila em lista

        items[message_id] = {
            "name": name,
            "categories": categories,
            "queue": queue
        }

    print("Dados restaurados com sucesso!")
    await check_reactions()  # Verifica se há reações erradas

@bot.command()
async def additem(ctx, channel: discord.TextChannel, name: str, description: str, image_url: str, *categories: str):

    category_list = list(categories)  # Converte a tupla de argumentos em uma lista

    """Adiciona um novo item e posta a mensagem no canal especificado."""
    embed = discord.Embed(title=name, description=description, color=discord.Color.blue())
    embed.set_image(url=image_url)
    embed.set_footer(text=f'Categorias: {", ".join(category_list)}')


    message = await channel.send(embed=embed)
    await message.add_reaction("✅")  # Reação para selecionar o item

    # Salvar os dados no canal de persistência
    log_channel = discord.utils.get(ctx.guild.text_channels, name=canal_persistencia_bot)
    if log_channel:
        save_message = await log_channel.send(f"{message.id} | {name} | {', '.join(category_list)} | []")
        await save_message.pin()  # Fixa a mensagem para ser fácil recuperar depois

    items[message.id] = {
        "name": name,
        "category": category_list,
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

        print(f"Roles do membro {user}:")
        print(member.roles)

        # Verifica se o membro tem um dos roles necessários
        allowed_roles = [role.name for role in member.roles]

        print(f"Roles permitidas para o item {item}:")
        print(allowed_roles)

        if any(role.name in item["category"] for role in member.roles):
            if user.id not in item["queue"]:
                item["queue"].append(user.id)
                await user.send(f'Você entrou na fila para {item["name"]}!')
            else:
                await user.send('Você já está na fila para esse item.')
        else:
            await user.send(f'Você não pode escolher este item ({item["name"]}), pois não usa a arma correspondente ou sua classe não usa esse item!')
            await reaction.message.remove_reaction(reaction.emoji, user)
            await reaction.remove(user)  # 🔥 Remove a reação automaticamente TEM QUE VER QUAL DAS DUAS FUNCIONA


@bot.event
async def on_reaction_remove(reaction, user):
    """Remove o membro da fila caso ele retire a reação."""
    if user.bot:
        return

    message_id = reaction.message.id
    if message_id in items:
        item = items[message_id]
        member = reaction.message.guild.get_member(user.id)

        if user.id in item["queue"]:
            item["queue"].remove(user.id)
            await user.send(f'Você foi removido da fila para {item["name"]}.')


@bot.command()
async def markreceived(ctx, member: discord.Member, item_name: str):
    """Remove o membro da fila de um item após recebê-lo."""
    log_channel = discord.utils.get(ctx.guild.text_channels, name=canal_persistencia_bot)

    if not log_channel:
        await ctx.send("Canal de persistência não encontrado!")
        return

    async for message in log_channel.history(limit=50):
        if message.content.startswith(str(item_name)):
            parts = message.content.split(" | ")
            message_id = int(parts[0])
            queue = eval(parts[3])  # Converte de string para lista

            if member.id in queue:
                queue.remove(member.id)
                new_content = f"{message_id} | {parts[1]} | {parts[2]} | {queue}"
                await message.edit(content=new_content)  # Atualiza a mensagem persistida
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


async def check_reactions():
    """Verifica se há reações inválidas e as remove."""
    for message_id, item in items.items():
        channel = discord.utils.get(bot.get_all_channels(), name="boss-drops")  # Canal onde os itens estão
        if not channel:
            continue

        try:
            message = await channel.fetch_message(message_id)
            for reaction in message.reactions:
                async for user in reaction.users():
                    if user.bot:
                        continue

                    member = message.guild.get_member(user.id)
                    if not any(role.name in item["categories"] for role in member.roles):
                        await message.remove_reaction(reaction.emoji, user)
                        print(f"Removida reação inválida de {user.name} no item {item['name']}")
        except discord.NotFound:
            print(f"Mensagem {message_id} não encontrada.")


bot.run(DISCORD_TOKEN)
