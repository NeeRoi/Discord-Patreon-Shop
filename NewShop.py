import nextcord
from nextcord.ext import commands,  tasks
from nextcord import ui
from nextcord.ui import button, View, Modal
import os
import json
import datetime
from config import TOKEN

intents = nextcord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Initialisiere Konfigurationsdaten
currency_refresh = {
    'Juvie': 2,
    'Sub-Adult': 5,
    'Adult': 9,
    'Elder': 16
}

item_prices = {
    'Reskin': 1,
    'Regender': 1,
    'Retalent': 1
}

item_limits = {
    'Juvie': {
        'Reskin': 2,
        'Regender': 0,
        'Retalent': 0
    },
    'Sub-Adult': {
        'Reskin': 4,
        'Regender': 1,
        'Retalent': 0
    },
    'Adult': {
        'Reskin': 6,
        'Regender': 2,
        'Retalent': 1
    },
    'Elder': {
        'Reskin': 9,
        'Regender': 4,
        'Retalent': 3
    }
}

patreon_shop_channel_id = 1129094664625074197
patreon_request_channel_id = 1129094520710111282
error_channel_id = 1129760990360240239
guild_id = 1129093489670500422

# Setze die Währungsdaten und Kaufhistorie der Benutzer
user_currency = {}
user_purchase_history = {}

# Lade Währungsdaten und Kaufhistorie, falls vorhanden
if os.path.isfile('user_currency.json'):
    with open('user_currency.json', 'r') as f:
        user_currency = json.load(f)
else:
    with open('user_currency.json', 'w') as f:
        json.dump({}, f)

if os.path.isfile('user_purchase_history.json'):
    with open('user_purchase_history.json', 'r') as f:
        user_purchase_history = json.load(f)
else:
    with open('user_purchase_history.json', 'w') as f:
        json.dump({}, f)

#Event Member Update Role
@bot.event
async def on_member_update(before, after):
    if set(before.roles) != set(after.roles):
        for role in after.roles:
            if str(role) in currency_refresh:
                if after.id not in user_currency:
                 user_currency[after.id] = currency_refresh[str(role)]
                with open('user_currency.json', 'w') as f:
                    json.dump(user_currency, f)

#Reset Currency every 1st of month
@tasks.loop(hours=24)
async def reset_currency():
    guild = bot.get_guild(guild_id)
    if datetime.now().day == 1:
        members = guild.fetch_members(limit=None)
        async for member in members:
            for role in member.roles:
                if str(role) in currency_refresh:
                    user_currency[member.id] = currency_refresh[str(role)]
        with open('user_currency.json', 'w') as f:
            json.dump(user_currency, f)

#Reset Limit every 1st of month
@tasks.loop(hours=24)
async def reset_purchase_history():
    if datetime.now().day == 1:
        user_purchase_history = {}
        with open('user_purchase_history.json', 'w') as f:
            json.dump(user_purchase_history, f)

class IngameIDModal(nextcord.ui.Modal):
    def __init__(self, ctx, item):
        super().__init__(title="Ingame-ID eingeben")
        self.ctx = ctx
        self.item = item
        self.ingame_id = None  # Will hold the Ingame ID entered by the user

        # Add a text input field for the Ingame ID
        self.add_item(nextcord.ui.TextInput(label="Ingame-ID", placeholder="Ingame-ID eingeben", custom_id="ingame_id"))

    async def interaction_check(self, interaction: nextcord.Interaction) -> bool:
        return interaction.user == self.ctx.author  # Only the user who invoked the command can interact with the modal

    async def callback(self, interaction: nextcord.Interaction):
        self.ingame_id = self.values["ingame_id"]  # Get the Ingame ID entered by the user
        if self.ingame_id is not None:
            # The user clicked the confirm button, so proceed with the purchase
            user_purchase_history[self.ctx.user.id][self.item] += 1
            with open('user_purchase_history.json', 'w') as f:
                json.dump(user_purchase_history, f)

            # Send the request to the Patreon request channel
            patreon_request_channel = self.ctx.guild.get_channel(patreon_request_channel_id)
            await patreon_request_channel.send(
                f"@Staff {self.ctx.user.name} möchte {self.item} kaufen. Seine Ingame-ID ist {self.ingame_id}."
            )

            # Send a confirmation message to the user
            await self.ctx.send(f"Dein Einkauf von {self.item} wurde erfolgreich angefordert. Bitte warte, bis ein Staff-Mitglied deine Anfrage bestätigt.")
        else:
            # The user clicked the cancel button, so cancel the purchase
            await self.ctx.send("Dein Einkauf wurde abgebrochen.")
        
@bot.slash_command()
async def shop(ctx, item: str):
    if ctx.channel_id == patreon_shop_channel_id:
        user_role = None
        for role in ctx.user.roles:
            if str(role) in item_limits:
                user_role = str(role)

        if not user_role:
            return await ctx.send("Du hast keine berechtigte Rolle zum Kauf!")

        if item not in item_limits[user_role]:
            return await ctx.send(f"Der Artikel {item} ist für deine Rolle nicht verfügbar!")

        if ctx.user.id not in user_currency:
            user_currency[ctx.user.id] = 0

        if user_currency[str(ctx.user.id)] < item_prices[item]:
            return await ctx.send("Du hast nicht genug Währung für diesen Kauf!")

        if ctx.user.id not in user_purchase_history:
            user_purchase_history[ctx.user.id] = {}

        if item not in user_purchase_history[ctx.user.id]:
            user_purchase_history[ctx.user.id][item] = 0

        if user_purchase_history[ctx.user.id][item] >= item_limits[user_role][item]:
            return await ctx.send("Du hast die maximale Anzahl von Käufen für diesen Artikel in diesem Monat erreicht!")

        # Open the modal for the user to enter their Ingame ID
        modal = IngameIDModal(ctx, item)
        await ctx.response.send_modal(modal)


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send('Ungültiger Befehl.')

@bot.event
async def on_member_update(before, after):
    if set(before.roles) != set(after.roles):
        for role in after.roles:
            if str(role) in currency_refresh:
                if after.id not in user_currency:
                    user_currency[after.id] = currency_refresh[str(role)]
                with open('user_currency.json', 'w') as f:
                    json.dump(user_currency, f)


bot.run(TOKEN)
