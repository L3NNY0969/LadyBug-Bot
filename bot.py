import discord
from discord.ext import commands
from utils.utils import *
from ext.context import Context
import json
import os
import inspect
import io
from contextlib import redirect_stdout
import textwrap
import traceback
import aiohttp

bot = commands.Bot(command_prefix="lb.", description="A simple Miraculous discord bot.", owner_id=292690616285134850)
bot._last_result = None
bot.session = aiohttp.ClientSession()
bot.commands_ran = 0
bot.cogs_list = [ "cogs." + x.replace(".py", "") for x in os.listdir("cogs") if x.endswith(".py") ]

def cleanup_code(content):
    '''Automatically removes code blocks from the code.'''
    # remove ```py\n```
    if content.startswith('```') and content.endswith('```'):
        return '\n'.join(content.split('\n')[1:-1])
    return content.strip('` \n')

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    ctx = await bot.get_context(message, cls=Context)
    if not ctx.command:
        return
    await bot.invoke(ctx)

@bot.event
async def on_ready():
    print("Bot is online!")
    print(f"Logged in as {bot.user.name}#{bot.user.discriminator} ({bot.user.id})")
    print(f"Servers: {len(bot.guilds)}")
    print(f"Users: {len(bot.users)}")
    print(f"Channels: {channel_count(bot)}")
    print(f"WebSocket Ping: {bot.latency:.4f} ms")
    await bot.change_presence(activity=discord.Game(f"lb.help | {len(bot.guilds)} servers!"))
    print("Loading cogs...")
    for x in bot.cogs_list:
        try:
            bot.load_extension(x)
        except Exception as e:
            print(f"LoadError in {x}:\n{e}")
   

@bot.event
async def on_guild_join(guild):
    print(f"Joined {guild.name} ({guild.id})")
    em = discord.Embed()
    em.color = 0x00ff00
    em.title = "Ladybug joined a new server!"
    em.description = guild.name
    if guild.icon_url:
        em.set_thumbnail(url=guild.icon_url)
    em.add_field(name="Owner", value=f"{guild.owner}")
    em.add_field(name="Member Count", value=f"{guild.member_count}")
    em.set_footer(text=f"{guild.id}")
    channel = bot.get_channel(454776806869041154)
    await channel.send(embed=em)
    await bot.change_presence(activity=discord.Game(f"lb.help | {len(bot.guilds)} servers!"))
    
@bot.event
async def on_guild_remove(guild):
    print(f"Left {guild.name} ({guild.id})")
    em = discord.Embed()
    em.color = 0xff0000
    em.title = "Ladybug left a server."
    em.description = guild.name
    if guild.icon_url:
        em.set_thumbnail(url=guild.icon_url)
    em.add_field(name="Owner", value=f"{guild.owner}")
    em.add_field(name="Member Count", value=f"{guild.member_count}")
    em.set_footer(text=f"{guild.id}")
    channel = bot.get_channel(454776806869041154)
    await channel.send(embed=em)
    await bot.change_presence(activity=discord.Game(f"lb.help | {len(bot.guilds)} servers!"))
    
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.NotOwner):
        return await ctx.send("This command is for owner only!")
    if isinstance(error, commands.MissingPermissions):
        perms = list(map(capitalize, error.missing_perms))
        return await ctx.send(f"Your missing permission(s) to run this command:\n{'\n'.join(perms)}")
    if isinstance(error, commands.CommandNotFound):
        return
  
    em = discord.Embed()
    em.color = 0xff0000
    em.title = "CommandError"
    em.description = f"An Error occured in command: {ctx.command}\n```py\n{error}\n```"
    em.set_footer(text=f"User: {ctx.author}, Guild: {ctx.guild}")
    logs = bot.get_channel(454776836929617921)
    await logs.send(embed=em)

@bot.event
async def on_command(ctx):
    bot.commands_ran += 1

@bot.command()
async def ping(ctx):
    """Checks if bot is working and measures websocket latency"""
    await ctx.send(f"Pong! WebSocket Latency: **{bot.latency:.4f} ms**")
    
@bot.command()
async def invite(ctx):
    """Want me in your server?"""
    await ctx.send(f"Invite me to your server: https://discordapp.com/oauth2/authorize?client_id={bot.user.id}&scope=bot&permissions=470281463")
    
@bot.command(name="eval", aliases=["ev"])
async def _eval(ctx, *, body):
    """Evaluates python code"""
    if ctx.author.id != 292690616285134850:
        return await ctx.send("This command is for owner only!")
    env = {
        'bot': bot,
        'ctx': ctx,
        'channel': ctx.channel,
        'author': ctx.author,
        'guild': ctx.guild,
        'message': ctx.message,
        'msg': ctx.message,
        '_': bot._last_result,
        'source': inspect.getsource,
        'src': inspect.getsource,
        'session': bot.session
    }

    env.update(globals())

    body = cleanup_code(body)
    stdout = io.StringIO()
    err = out = None

    to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

    def paginate(text: str):
        '''Simple generator that paginates text.'''
        last = 0
        pages = []
        for curr in range(0, len(text)):
            if curr % 1980 == 0:
                pages.append(text[last:curr])
                last = curr
                appd_index = curr
        if appd_index != len(text) - 1:
            pages.append(text[last:curr])
        return list(filter(lambda a: a != '', pages))

    try:
        exec(to_compile, env)
    except Exception as e:
        err = await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')
        return await ctx.message.add_reaction('\u2049')

    func = env['func']
    try:
        with redirect_stdout(stdout):
            ret = await func()
    except Exception as e:
        value = stdout.getvalue()
        err = await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
    else:
        value = stdout.getvalue()
        if ret is None:
            if value:
                try:

                    out = await ctx.send(f'```py\n{value}\n```')
                except:
                    paginated_text = paginate(value)
                    for page in paginated_text:
                        if page == paginated_text[-1]:
                            out = await ctx.send(f'```py\n{page}\n```')
                            break
                        await ctx.send(f'```py\n{page}\n```')
        else:
            bot._last_result = ret
            try:
                out = await ctx.send(f'```py\n{value}{ret}\n```')
            except:
                paginated_text = paginate(f"{value}{ret}")
                for page in paginated_text:
                    if page == paginated_text[-1]:
                        out = await ctx.send(f'```py\n{page}\n```')
                        break
                    await ctx.send(f'```py\n{page}\n```')

    if out:
        await ctx.message.add_reaction('\u2705')  # tick
    elif err:
        await ctx.message.add_reaction('\u2049')  # x
    else:
        await ctx.message.add_reaction('\u2705')

if __name__ == "__main__":    
    bot.run(os.environ.get("TOKEN"))