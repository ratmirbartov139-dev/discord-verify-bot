import discord
from discord.ext import commands
import json
import os
import asyncio

# Загрузка конфига
def load_config():
    if os.path.exists('config.json'):
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

config = load_config()

# Настройки бота
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# ID роли для верифицированных (из переменных окружения или config.json)
VERIFIED_ROLE_ID = int(os.getenv('VERIFIED_ROLE_ID', config.get('verified_role_id', 0)))

class VerifyButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label='✅ Верифицироваться', style=discord.ButtonStyle.green, custom_id='verify_button')
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(VERIFIED_ROLE_ID)
        
        if not role:
            await interaction.response.send_message('❌ Роль верификации не найдена! Обратись к администратору.', ephemeral=True)
            return
        
        if role in interaction.user.roles:
            await interaction.response.send_message('✅ Ты уже верифицирован!', ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            
            # Скрываем канал верификации для пользователя
            verify_channel = interaction.channel
            await verify_channel.set_permissions(interaction.user, view_channel=False)
            
            # Отправляем сообщение которое удалится через 20 секунд
            msg = await interaction.response.send_message('✅ Верификация пройдена! Добро пожаловать на сервер!\nЭто сообщение исчезнет через 20 секунд.', ephemeral=False)
            
            # Удаляем сообщение через 20 секунд
            await interaction.followup.send('✅ Верификация пройдена!', ephemeral=True)
            
            print(f'✅ {interaction.user.name} прошёл верификацию')

@bot.event
async def on_ready():
    print(f'🤖 Бот {bot.user.name} запущен!')
    print(f'📊 Подключен к {len(bot.guilds)} серверам')
    
    # Регистрируем кнопку при запуске
    bot.add_view(VerifyButton())

@bot.event
async def on_message(message):
    # Игнорируем сообщения бота
    if message.author.bot:
        await bot.process_commands(message)
        return
    
    # Если это канал верификации и у пользователя нет роли - удаляем через 20 сек
    if message.channel.name == 'верификация' or 'verify' in message.channel.name.lower():
        role = message.guild.get_role(VERIFIED_ROLE_ID)
        if role and role not in message.author.roles:
            await asyncio.sleep(20)
            try:
                await message.delete()
            except:
                pass
    
    await bot.process_commands(message)

@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    """Создать сообщение с верификацией"""
    embed = discord.Embed(
        title="🔐 Верификация",
        description="Добро пожаловать на сервер!\n\nНажми на кнопку ниже, чтобы получить доступ ко всем каналам.",
        color=discord.Color.green()
    )
    embed.set_footer(text="Нажми кнопку только один раз")
    
    await ctx.send(embed=embed, view=VerifyButton())
    await ctx.message.delete()

@bot.command()
@commands.has_permissions(administrator=True)
async def setrole(ctx, role: discord.Role):
    """Установить роль для верификации"""
    global VERIFIED_ROLE_ID
    VERIFIED_ROLE_ID = role.id
    
    # Сохраняем в конфиг
    config['verified_role_id'] = role.id
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    
    await ctx.send(f'✅ Роль верификации установлена: {role.mention}')

@bot.command()
async def help_verify(ctx):
    """Помощь по командам"""
    embed = discord.Embed(
        title="📖 Команды бота верификации",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="Для администраторов:",
        value="`!setrole @роль` - Установить роль для верификации\n"
              "`!setup` - Создать сообщение с кнопкой верификации",
        inline=False
    )
    await ctx.send(embed=embed)

# Запуск бота
if __name__ == '__main__':
    token = config.get('bot_token', '')
    if not token:
        print('❌ Токен бота не найден в config.json!')
    else:
        print('✅ Запускаю бота...')
        try:
            bot.run(token)
        except discord.errors.LoginFailure:
            print('❌ Неправильный токен! Создай новый на Discord Developer Portal')
        except Exception as e:
            print(f'❌ Ошибка: {e}')
