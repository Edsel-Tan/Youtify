KEY = None
with open(f"data//key.txt") as file:
    KEY = file.readline()


# imports
import discord
import discord.ext

# setting up the bot
intents = discord.Intents.all() 
# if you don't want all intents you can do discord.Intents.default()
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

# sync the slash command to your server
@client.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=697442183627800656))
    # print "ready" in the console when the bot is ready to work
    print("ready")

# make the slash command
@tree.command(name="name", description="description")
async def slash_command(interaction: discord.Interaction):    
    await interaction.response.send_message("command")

# run the bot
client.run(f"{KEY}")
