import discord
import os
import logging
import json
import asyncio
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

# Logging
logger = logging.getLogger(__name__)

# Canal do discord que terá os dados para serem carregados.
canal_persistencia_bot = "bot-data"
canal_boss_drops = "🤝boss-drops"

@bot.event
async def on_ready():
    """Carrega os dados do canal de persistência ao iniciar."""
    print(f'Bot conectado como {bot.user}')

    # Carrega a ferramenta de logging
    logging.basicConfig(filename='logs/boss_drop_manager.log', level=logging.INFO)
    logger.info('on_ready: Started')

    log_channel = discord.utils.get(bot.get_all_channels(), name=canal_persistencia_bot)
    if not log_channel:
        print("Canal de persistência não encontrado!")
        return

    async for message in log_channel.history(limit=100):
        # Ignora mensagens do tipo 'pins_add' (fixação de mensagens) ou outros tipos que não sejam comuns
        if message.type == discord.MessageType.pins_add:
            continue  # Ignora a mensagem e passa para a próxima

        #print("message")
        #print(message)
        parts = message.content.split(" | ")
        #print("parts")
        #print(parts)

        message_id = int(parts[0])
        name = parts[1]
        categories = parts[2].split(", ")
        queue = eval(parts[3])  # Converte a string da fila em lista

        items[message_id] = {
            "name": name,
            "categories": categories,
            "queue": queue
        }
        #print(f'items[{message_id}]')
        #print(items[message_id])

    print("Dados restaurados com sucesso!")
    await check_reactions()  # Verifica se há reações erradas
    logger.info('on_ready: Finished')

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

    logger.info(f'additem: ✅ {ctx.author.mention}, o item **"{name}"** foi adicionado com sucesso em {channel.mention}!')

    # Envia a confirmação abaixo do comando no mesmo canal
    await ctx.send(f'✅ {ctx.author.mention}, o item **"{name}"** foi adicionado com sucesso em {channel.mention}!')

@bot.event
async def on_reaction_add(reaction, user):
    """Adiciona o membro à fila se ele tiver o cargo correto e atualiza a persistência."""
    if user.bot:
        return

    print(f"🟢 REAÇÃO ADICIONADA: {user.name} -> {reaction.emoji}")

    message_id = reaction.message.id
    if message_id in items:
        item = items[message_id]
        member = reaction.message.guild.get_member(user.id)

        if not member:
            return

        # Verifica se o usuário tem uma das roles necessárias
        if any(role.name in item["category"] for role in member.roles):
            if user.id not in item["queue"]:
                item["queue"].append(user.id)
                await user.send(f'✅ Você entrou na fila para {item["name"]}!')
        else:
            await user.send(f'❌ Você não pode escolher este item ({item["name"]}), pois não tem a role necessária!')
            await reaction.message.remove_reaction(reaction.emoji, user)
            return  # Retorna aqui para não atualizar o canal se for reação inválida

        # Atualizar os dados no canal de persistência
        log_channel = discord.utils.get(reaction.message.guild.text_channels, name=canal_persistencia_bot)
        if log_channel:
            async for msg in log_channel.history(limit=100):  # Procura a mensagem do item salvo
                if msg.content.startswith(f"{message_id} |"):
                    fila_str = ', '.join([str(uid) for uid in item["queue"]])
                    novo_conteudo = f"{message_id} | {item['name']} | {', '.join(item['category'])} | [{fila_str}]"
                    await msg.edit(content=novo_conteudo)  # Atualiza a mensagem com a nova fila
                    break
        print(f"✅ Mensagem do item {item['name']} atualizada no {canal_persistencia_bot}")


@bot.event
async def on_reaction_remove(reaction, user):
    """Remove o membro da fila caso ele retire a reação e atualiza a persistência."""
    if user.bot:
        return

    print(f"🟡 REAÇÃO REMOVIDA: {user.name} -> {reaction.emoji}")

    message_id = reaction.message.id
    if message_id in items:
        item = items[message_id]
        member = reaction.message.guild.get_member(user.id)

        if user.id in item["queue"]:
            item["queue"].remove(user.id)
            await user.send(f'⚠️ Você foi removido da fila para {item["name"]}.')

        # Atualizar os dados no canal de persistência
        log_channel = discord.utils.get(reaction.message.guild.text_channels, name=canal_persistencia_bot)
        if log_channel:
            async for msg in log_channel.history(limit=100):  # Procura a mensagem do item salvo
                if msg.content.startswith(f"{message_id} |"):
                    fila_str = ', '.join([str(uid) for uid in item["queue"]])
                    novo_conteudo = f"{message_id} | {item['name']} | {', '.join(item['category'])} | [{fila_str}]"
                    await msg.edit(content=novo_conteudo)  # Atualiza a mensagem com a nova fila
                    break
        print(f"✅ Mensagem do item {item['name']} atualizada no {canal_persistencia_bot}")


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


async def load_data_on_startup():
    """Carrega os dados dos itens e filas ao iniciar o bot e verifica reações no canal de drops."""
    await bot.wait_until_ready()  # Aguarda o bot estar pronto
    guild = bot.guilds[0]  # Obtém o primeiro servidor que o bot está (ajuste se necessário)

    log_channel = discord.utils.get(guild.text_channels, name=canal_persistencia_bot)
    drops_channel = discord.utils.get(guild.text_channels, name=canal_boss_drops)

    if not log_channel:
        print("Canal de persistência não encontrado!")
        return

    if not drops_channel:
        print("Canal de drops não encontrado!")
        return

    # 🔹 Restaurar dados da fila de persistência
    async for msg in log_channel.history(limit=100):
        try:
            parts = msg.content.split(" | ")

            if len(parts) < 4:  # Verifica se há 4 partes esperadas
                print(f"⚠️ Mensagem inválida ignorada: {msg.content}")
                continue  # Ignora mensagens quebradas

            if not parts[0].isdigit():  # Verifica se a primeira parte é um número válido
                print(f"⚠️ ID inválido ignorado: {parts[0]}")
                continue

            message_id = int(parts[0])
            name = parts[1]
            categories = parts[2].split(", ")

            try:
                queue = eval(parts[3]) if parts[3].strip() else []  # Garante que a fila vazia não cause erro
            except Exception as e:
                print(f"⚠️ Erro ao processar fila do item '{name}': {e}")
                queue = []

            items[message_id] = {
                "name": name,
                "category": categories,
                "queue": queue
            }
            print(f"✅ Item restaurado: {name}, Fila: {queue}")
        except Exception as e:
            print(f"❌ Erro ao carregar item: {e}")

    # 🔹 Verificar reações antigas no canal de drops
    async for message in drops_channel.history(limit=100):
        if message.id in items:  # Se a mensagem for um item registrado
            item = items[message.id]

            for reaction in message.reactions:
                async for user in reaction.users():
                    if user.bot:
                        continue  # Ignora bots

                    member = guild.get_member(user.id)
                    if not member:
                        continue  # Se o membro não for encontrado, ignora

                    # Verifica se o usuário tem a role necessária para o item
                    if any(role.name in item["category"] for role in member.roles):
                        if user.id not in item["queue"]:
                            item["queue"].append(user.id)
                            await user.send(f'🔔 Você foi adicionado à fila para {item["name"]}.')
                    else:
                        await message.remove_reaction(reaction.emoji, user)
                        await user.send(
                            f'🚫 Você não pode escolher este item ({item["name"]}), pois não tem a role necessária!'
                        )

    print("✅ Reações antigas verificadas e filas atualizadas!")


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
    """Verifica reações antigas no canal de drops e atualiza a fila corretamente."""
    await bot.wait_until_ready()  # Garante que o bot está pronto
    guild = bot.guilds[0]  # Obtém o primeiro servidor que o bot está (ajuste se necessário)

    drops_channel = discord.utils.get(guild.text_channels, name=canal_boss_drops)
    if not drops_channel:
        print("🚨 Canal de drops não encontrado!")
        return

    print("🔄 Verificando reações antigas nos itens...")

    async for message in drops_channel.history(limit=100):
        if message.id in items:  # Se a mensagem for um item registrado
            item = items[message.id]

            for reaction in message.reactions:
                async for user in reaction.users():
                    if user.bot:
                        continue  # Ignora bots

                    member = guild.get_member(user.id)
                    if not member:
                        continue  # Se o membro não for encontrado, ignora

                    # Verifica se o usuário tem a role necessária para o item
                    if any(role.name in item["categories"] for role in member.roles):
                        if user.id not in item["queue"]:
                            item["queue"].append(user.id)
                            await user.send(f'🔔 Você foi adicionado à fila para {item["name"]}!')
                    else:
                        await message.remove_reaction(reaction.emoji, user)
                        await user.send(f'🚫 Você não pode escolher este item ({item["name"]}), pois não tem a role necessária!')

    print("✅ Reações antigas verificadas e filas atualizadas!")


async def check_reactions_old():
    """Verifica se há reações inválidas e as remove."""
    for message_id, item in items.items():
        channel = discord.utils.get(bot.get_all_channels(), name=canal_boss_drops)  # Canal onde os itens estão
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




async def monitor_old_messages():
    """Verifica periodicamente as mensagens do canal de drops para monitorar reações."""
    await bot.wait_until_ready()  # Espera o bot estar pronto
    guild = bot.guilds[0]  # Pega o primeiro servidor (ajuste se necessário)

    drops_channel = discord.utils.get(guild.text_channels, name=canal_boss_drops)
    if not drops_channel:
        print("🚨 Canal de drops não encontrado!")
        return

    print("🔄 Iniciando monitoramento contínuo das reações...")

    while not bot.is_closed():
        async for message in drops_channel.history(limit=100):  # Percorre mensagens antigas
            if message.id in items:
                item = items[message.id]

                for reaction in message.reactions:
                    async for user in reaction.users():
                        if user.bot:
                            continue  # Ignora bots

                        member = guild.get_member(user.id)
                        if not member:
                            continue  # Se o membro não for encontrado, ignora

                        # Se o usuário tem a role necessária
                        if any(role.name in item["category"] for role in member.roles):
                            if user.id not in item["queue"]:
                                item["queue"].append(user.id)
                                try:
                                    await user.send(f'🔔 Você foi adicionado à fila para {item["name"]}!')
                                except discord.Forbidden:
                                    print(f"❌ Não consegui enviar mensagem para {user}.")
                        else:  # Se não tem a role necessária, remove a reação
                            await message.remove_reaction(reaction.emoji, user)
                            try:
                                await user.send(f'🚫 Você não pode escolher este item ({item["name"]}), pois não tem a role necessária!')
                            except discord.Forbidden:
                                print(f"❌ Não consegui enviar mensagem para {user}.")

        await asyncio.sleep(10)  # Aguarda 10 segundos antes de checar novamente



async def re_register_reactions():
    """Verifica mensagens antigas, adiciona usuários na fila e remove quem retirou a reação enquanto o bot estava offline."""
    await bot.wait_until_ready()
    guild = bot.guilds[0]  # Ajuste se necessário
    drops_channel = discord.utils.get(guild.text_channels, name=canal_boss_drops)

    if not drops_channel:
        print("🚨 Canal de drops não encontrado!")
        return

    log_channel = discord.utils.get(guild.text_channels, name=canal_persistencia_bot)
    if not log_channel:
        print("🚨 Canal de persistência não encontrado!")
        return

    print("🔄 Re-registrando mensagens antigas e monitorando reações...")

    async for message in drops_channel.history(limit=100):
        print("message.id:", message.id)
        print("items:", items)
        if message.id in items:
            item = items[message.id]
            reacted_users = set()  # IDs de usuários que ainda têm a reação
            print("cheguei akiiiii 3")
            for reaction in message.reactions:
                async for user in reaction.users():
                    if user.bot:
                        continue  # Ignorar bots

                    member = guild.get_member(user.id)
                    if not member:
                        continue  # Usuário não encontrado

                    # 🔥 Se o usuário tem a role necessária, ele pode entrar na fila
                    if any(role.name in item["category"] for role in member.roles):
                        reacted_users.add(user.id)

                        # 🔹 Se o usuário reagiu e não estava na fila, adicionamos ele corretamente
                        if user.id not in item["queue"]:
                            item["queue"].append(user.id)
                            try:
                                await user.send(f'✅ Você foi adicionado à fila para {item["name"]}!')
                            except discord.Forbidden:
                                print(f"⚠️ Não foi possível enviar DM para {user}")

                    else:
                        # 🔥 Remove reações inválidas
                        await message.remove_reaction(reaction.emoji, user)
                        try:
                            await user.send(f'🚫 Você não pode escolher este item ({item["name"]}), pois não tem a role necessária!')
                        except discord.Forbidden:
                            print(f"⚠️ Não foi possível enviar DM para {user}")

            print(f"FILA do item {item}:")
            print(f'{item["queue"]}')
            print("REACTED USERS:")
            print(f'{reacted_users}')

            # 🔥 Detecta remoção de reação enquanto o bot estava offline
            users_to_remove = [uid for uid in item["queue"] if uid not in reacted_users]
            print("cheguei akiiiii 2: ", users_to_remove)
            if users_to_remove:
                for user_id in users_to_remove:
                    item["queue"].remove(user_id)
                    member = guild.get_member(user_id)
                    if member:
                        try:
                            await member.send(f'⚠️ Você foi removido da fila para {item["name"]} porque retirou a reação enquanto o bot estava offline.')
                        except discord.Forbidden:
                            print(f"⚠️ Não foi possível enviar DM para {member}")

            # 🔄 Atualizar os dados no canal de persistência corretamente
            print(f"🔄 Atualizando canal de persistência para {item['name']}...")
            message_found = False  # Flag para verificar se encontramos a mensagem

            print("cheguei akiiiii")
            async for msg in log_channel.history(limit=100):
                msg_parts = msg.content.split(" | ")
                print('To no canal de persistencia pra atualizar!')
                print(msg_parts)
                #print("ITEM:")
                #print(item)
                if len(msg_parts) >= 4 and msg_parts[0] == str(message.id):
                    message_found = True
                    fila_str = ', '.join([str(uid) for uid in item["queue"]])
                    novo_conteudo = f"{message.id} | {item['name']} | {', '.join(item['category'])} | [{fila_str}]"
                    await msg.edit(content=novo_conteudo)  # Atualiza a mensagem com a nova fila
                    print(f"✅ Mensagem do item {item['name']} foi atualizada no {canal_persistencia_bot}")
                    break  # Sai do loop assim que encontra a mensagem correta

            if not message_found:
                print(f"⚠️ Nenhuma mensagem correspondente encontrada para {item['name']} no {canal_persistencia_bot}!")

    print("✅ Mensagens verificadas, usuários adicionados à fila e persistência atualizada!")


@bot.command()
async def load_all_items(ctx, channel: discord.TextChannel):
    """Carrega todos os itens do arquivo JSON e os adiciona ao canal especificado."""
    try:
        with open("items.json", "r", encoding="utf-8") as file:
            items_list = json.load(file)

        if not items_list:
            await ctx.send("❌ Nenhum item encontrado no arquivo `items.json`.")
            return

        for item in items_list:
            name = item["name"]
            description = item["description"]
            image_url = item["image_url"]
            categories = item["categories"]

            # Criar embed para o item
            embed = discord.Embed(title=name, description=description, color=discord.Color.blue())
            embed.set_image(url=image_url)
            embed.set_footer(text=f'Categorias: {", ".join(categories)}')

            # Enviar mensagem no canal do Discord
            message = await channel.send(embed=embed)
            await message.add_reaction("✅")  # Adiciona reação para escolha do item

            # Salvar no canal de persistência
            log_channel = discord.utils.get(ctx.guild.text_channels, name=canal_persistencia_bot)
            if log_channel:
                save_message = await log_channel.send(f"{message.id} | {name} | {', '.join(categories)} | []")
                await save_message.pin()  # Fixa a mensagem para facilitar a recuperação

            # Adicionar item ao dicionário de controle do bot
            items[message.id] = {
                "name": name,
                "category": categories,
                "queue": []
            }

            print(f"✅ Item {name} adicionado ao canal {channel.name}!")

        await ctx.send(f"✅ Todos os itens foram carregados e adicionados ao canal {channel.mention}!")

    except Exception as e:
        await ctx.send(f"❌ Erro ao carregar itens: {str(e)}")
        print(f"Erro ao carregar JSON: {str(e)}")

@bot.event
async def setup_hook():
    bot.loop.create_task(load_data_on_startup())
    bot.loop.create_task(monitor_old_messages())
    bot.loop.create_task(re_register_reactions())



bot.run(DISCORD_TOKEN)
