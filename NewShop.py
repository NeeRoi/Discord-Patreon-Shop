import nextcord
from nextcord.ext import commands, tasks
from nextcord import ui, interactions, SlashOption, Member, Role
from nextcord.ui import button, View, Modal
from nextcord import Embed, Button, ButtonStyle, ActionRow
import os
import json
import datetime
from datetime import datetime, timedelta
from config import TOKEN

intents = nextcord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)

#Initialisiere Konfigurationsdaten
role_details = {
    '1129764767628787742': {
        'name': 'Juvie',
        'currency': 2,
        'limits': {
            'Reskin': 2,
            'Regender': 0,
            'Retalent': 0
        }
    },
    '1129764708858200154': {
        'name': 'Sub-Adult',
        'currency': 5,
        'limits': {
            'Reskin': 4,
            'Regender': 1,
            'Retalent': 0
        }
    },
    '1129764624468807690': {
        'name': 'Adult',
        'currency': 9,
        'limits': {
            'Reskin': 6,
            'Regender': 2,
            'Retalent': 1
        }
    },
    '1129765057597816872': {
        'name': 'Elder',
        'currency': 16,
        'limits': {
            'Reskin': 9,
            'Regender': 4,
            'Retalent': 3
        }
    }
}

item_prices = {
    'Reskin': 1,
    'Regender': 1,
    'Retalent': 1
}

#Set the channel/server IDs
patreon_shop_channel_id = 1129094664625074197
patreon_request_channel_id = 1129094520710111282
log_channel_id = 1129760990360240239
guild_id = 1129093489670500422

#allowed_roles = ["Staff", "Admin", "Moderator", "Developer", "Owner"] aktuell nur staff
allowed_roles = ["1132058617563070484"]

#Staff role
staff_role_id = 1129093774623117354

#Setze die Währungsdaten und Kaufhistorie der Benutzer
user_currency = {}
user_purchase_history = {}

#Lade Währungsdaten und Kaufhistorie, falls vorhanden
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
            if str(role.id) in role_details:
                if str(after.id) not in user_currency:
                    user_currency[str(after.id)] = role_details[str(role.id)]['currency']
                    with open('user_currency.json', 'w') as f:
                        json.dump(user_currency, f)
                if str(after.id) not in user_purchase_history:
                    user_purchase_history[str(after.id)] = {}

#Reset Currency every 1st of month
@tasks.loop(hours=1)
async def reset_currency():
    guild = bot.get_guild(guild_id)
    # Get the current time in UTC
    now_utc = datetime.utcnow()
    # Convert to UTC-7
    now_pacific = now_utc - timedelta(hours=7)
    #print("Checking if 10 mins are up 'Resetting currency'")
    #if datetime.datetime.now().minute % 10 == 0:
    if now_pacific.day == 1 and now_pacific.hour == 1 and now_pacific.minute == 1: #Check if it's the first day of the month and if the time is 01:00
        print("Resetting currency")
        members = guild.fetch_members(limit=None)
        async for member in members:
            for role in member.roles:
                if str(role.id) in role_details:
                    user_currency[str(member.id)] = role_details[str(role.id)]['currency']
        with open('user_currency.json', 'w') as f:
            json.dump(user_currency, f)

#Reset Limit every 1st of month
@tasks.loop(hours=1)
async def reset_purchase_history():
    # Get the current time in UTC
    now_utc = datetime.utcnow()
    # Convert to UTC-7
    now_pacific = now_utc - timedelta(hours=7)
    #print("Checking if 10 mins are up 'Resetting limit'")
    #if datetime.datetime.now().minute % 10 == 0:
    if now_pacific.day == 1 and now_pacific.hour == 1 and now_pacific.minute == 1: #Check if it's the first day of the month and if the time is 01:00
        user_purchase_history = {}
        print("Resetting purchase history")
        with open('user_purchase_history.json', 'w') as f:
            json.dump(user_purchase_history, f)


#Specify the modal and the input
class IngameIDModal(nextcord.ui.Modal):
    def __init__(self, ctx, item):
        super().__init__(title="Enter Ingame-ID!")
        self.ctx = ctx
        self.item = item
        self.ingame_id = None  #Will hold the message sent to the Patreon channel

        #Add a text input field for the Ingame ID
        self.IngID = nextcord.ui.TextInput(label="Ingame-ID", placeholder="Enter Ingame-ID!", required=True, custom_id="ingame_id")
        self.add_item(self.IngID)

    #Starts after the modal closes
    async def callback(self, interaction: nextcord.Interaction):
        self.ingame_id = self.IngID.value  #Speichern Sie die Ingame-ID, die vom Benutzer eingegeben wurde
        if self.ingame_id.isnumeric() and len(self.ingame_id) in range(3, 5):  #Überprüfen Sie, ob die eingegebene Ingame-ID gültig ist
            #Create embed message
            embed = Embed(title="Patreon Shop Request", description=f"{interaction.user.mention} has `{self.item}` purchased. Their in-game ID is `{self.ingame_id}`. Please confirm or cancel the request!", color=0xFFFF00)
            
            #Initialize the UserView first
            user_view = UserView(interaction.user, self.item, self.ingame_id)
            user_embed = Embed(title="Patreon Shop Request", description=f"Your purchase of `{self.item}` was successfully requested. Their in-game ID is `{self.ingame_id}`. Please wait until a staff member confirms your request.", color=0xFFFF00)
            try:
                if user_view.user_message is not None:
                    await user_view.user_message.edit(embed=user_embed, view=user_view)
                else:
                    user_view.user_message = await interaction.user.send(embed=user_embed, view=user_view)
            except nextcord.errors.Forbidden:
                await interaction.channel.send(f"{interaction.user.mention}, I could not send you a direct message. Please check your privacy settings and try again.", delete_after=60)

            # Then initialize the CustomView
            view = CustomView(interaction.user, self.item, self.ingame_id, None, user_view)
            user_view.set_patreon_view(view)  # Pass the user_view to the CustomView

            # Send the request to the Patreon request channel and ping the staff role
            patreon_request_channel = self.ctx.guild.get_channel(patreon_request_channel_id)
            patreon_message = await patreon_request_channel.send(content=f"<@&{staff_role_id}>",embed=embed, view=view)  # attach the view to the message and ping the staff role!

            # Update the patreon_message in the CustomView
            view.patreon_message = patreon_message
        
            #Close the modal and send an ephemeral message to the user
            return await interaction.response.send_message(f"Your purchase of `{self.item}` was successfully requested. Their in-game ID is `{self.ingame_id}`. Please wait until a staff member confirms your request.", ephemeral=True, delete_after=60)
        else:
            #Send an ephemeral message to the user indicating that the Ingame ID is invalid
            return await interaction.response.send_message("Invalid Ingame-ID. Please enter a 3-4 digit number.", ephemeral=True, delete_after=60)

#Creating Patreon channel Buttons
class CustomView(nextcord.ui.View):
    def __init__(self, user: nextcord.User, item: str, ingame_id: str, patreon_message: nextcord.Message, user_view: nextcord.ui.View = None):
        super().__init__()
        self.user = user
        self.item = item
        self.ingame_id = ingame_id
        self.patreon_message = patreon_message
        self.user_view = user_view

    @nextcord.ui.button(label="Confirm Request", style=nextcord.ButtonStyle.green)
    async def confirm_order(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        #Update the embed of the Patreon channel's message
        new_embed = Embed(title="Request Confirmed", description=f"{self.user.mention} purchase of `{self.item}` has been completed! Their in-game ID is `{self.ingame_id}`.\n\nThis request has been completed by {interaction.user.mention}.", color=0x7CFC00)  #Create a new embed with the confirmation message
        await self.patreon_message.edit(embed=new_embed, view=None)  #Edit the original message's embed
        await interaction.response.send_message(f"Successfully completed the patreon shop request for {self.user.mention}, for {self.item}.", ephemeral=True)
        # Update user's currency
        user_currency[str(self.user.id)] -= item_prices[self.item]
        with open('user_currency.json', 'w') as f:
            json.dump(user_currency, f)

        # Update user's purchase history
        user_purchase_history[str(self.user.id)][self.item] += 1
        with open('user_purchase_history.json', 'w') as f:
            json.dump(user_purchase_history, f)

        # Update the user's message
        new_user_embed = Embed(title="Request Confirmed", description=f"Your purchase of `{self.item}` has been completed! Their in-game ID is `{self.ingame_id}`.\n\nIf your request has not been completed within 5 minutes after receiving this message, please contact our Support Bot!", color=0x7CFC00)  #Create a new embed with the confirmation message
        if self.user_view.user_message is not None:  # Ensure self.user_view.user_message is not None before trying to edit it
            try:
                await self.user_view.user_message.edit(embed=new_user_embed, view=None)  #Edit the original message's embed and remove the view
            except nextcord.errors.Forbidden:
                patreon_shop_channel = bot.get_channel(patreon_shop_channel_id)
                await patreon_shop_channel.send(f"{self.user.mention}, I could not send you a direct message. Please check your privacy settings and try again.", delete_after=60)
        else:
            patreon_shop_channel = bot.get_channel(patreon_shop_channel_id)
            await patreon_shop_channel.send(f"{self.user.mention}, Your Request has been confirmed and will be processed shortly.\n\nIf your request has not been completed within 5 minutes after receiving this message, please contact our Support Bot!", delete_after=60)

    @nextcord.ui.button(label="Request Cancelled", style=nextcord.ButtonStyle.red)
    async def cancel_order(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        #Update the embed of the Patreon channel's message
        new_embed = Embed(title="Request Cancelled", description=f"{self.user.mention} purchase of `{self.item}` has been canceled! Their in-game ID is `{self.ingame_id}`.\n\nThis request has been cancelled by {interaction.user.mention}.", color=0xFF0000)  #Create a new embed with the cancellation message
        await self.patreon_message.edit(embed=new_embed, view=None)  #Edit the original message's embed
        await interaction.response.send_message(f"Successfully cancelled the patreon shop request for {self.user.mention}, for {self.item}.", ephemeral=True)

        # Update the user's message
        new_user_embed = Embed(title="Request Cancelled", description=f"Your purchase of `{self.item}` has been canceled!\n\nIf you did not receive a refund for your request please contact the Support Bot!", color=0xFF0000)  #Create a new embed with the cancellation message
        try:
            if self.user_view.user_message is not None:
                await self.user_view.user_message.edit(embed=new_user_embed, view=None)  #Edit the original message's embed and remove the view
            else:
                patreon_shop_channel = bot.get_channel(patreon_shop_channel_id)
                await patreon_shop_channel.send(f"{self.user.mention}, your Request has been cancelled!", delete_after=60)  
        except nextcord.errors.Forbidden as e:
            print(f"An error occurred: {e}")
            patreon_shop_channel = bot.get_channel(patreon_shop_channel_id)
            await patreon_shop_channel.send(f"{self.user.mention}, your Request has been cancelled!", delete_after=60)

#Creating User channel Buttons
class UserView(nextcord.ui.View):
    def __init__(self, user: nextcord.User, item: str, ingame_id: str):
        super().__init__()
        self.user = user
        self.item = item
        self.ingame_id = ingame_id
        self.user_message = None
        self.patreon_view = None

    def set_patreon_view(self, patreon_view):
        self.patreon_view = patreon_view

    @nextcord.ui.button(label="Request Cancelled", style=nextcord.ButtonStyle.red)
    async def cancel_order(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        #Update the embed of the user's message
        new_embed = Embed(title="Request Cancelled", description=f"You have cancelled your request of `{self.item}`.\n\nIf you did not receive a refund for your request please contact the Support Bot!", color=0xFF0000)  #Create a new embed with the cancellation message
        try:
            await self.user_message.edit(embed=new_embed, view=None)  #Edit the original message's embed and remove the view
            await interaction.response.send_message(f"{self.user.mention}, You successfully cancelled your patreon shop request for `{self.item}`!")
        except nextcord.errors.Forbidden:
            await interaction.channel.send(f"{interaction.user.mention}, I could not send you a direct message. Please check your privacy settings and try again.", delete_after=30)

        # Update the Patreon message
        new_patreon_embed = Embed(title="Request Cancelled", description=f"{self.user.mention}'s purchase of `{self.item}` has been cancelled! Their in-game ID is `{self.ingame_id}`.\n\nThis request has been cancelled by {interaction.user.mention}.", color=0xFF0000)  #Create a new embed with the cancellation message
        await self.patreon_view.patreon_message.edit(embed=new_patreon_embed, view=None)  #Edit the original message's embed

#ShopView for buttons
class ShopView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(label="Reskin", style=nextcord.ButtonStyle.primary, custom_id="reskin_button")
    async def reskin_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await shop(interaction, "Reskin")

    @nextcord.ui.button(label="Regender", style=nextcord.ButtonStyle.primary, custom_id="regender_button")
    async def regender_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await shop(interaction, "Regender")

    @nextcord.ui.button(label="Retalent", style=nextcord.ButtonStyle.primary, custom_id="retalent_button")
    async def retalent_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await shop(interaction, "Retalent")

#/shop Command      
@bot.slash_command()
async def shop(interaction: nextcord.Interaction, item: str = SlashOption(name='item', required=True, choices={'Reskin', 'Regender', 'Retalent'})):
    if interaction.channel_id == patreon_shop_channel_id:
        user_role = None
        for role in interaction.user.roles:
            if str(role.id) in role_details:
                user_role = role_details[str(role.id)]
        #Check if the user has a role that is allowed to purchase the item
        if not user_role:
            return await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True, delete_after=30)
        #Check if the user has already purchased the maximum number of items for the month
        if item not in user_role['limits']:
            return await interaction.response.send_message(f"The Item `{item}` is not available for your role!", ephemeral=True, delete_after=30)
        #Check if the user is in the currency dictionary
        if str(interaction.user.id) not in user_currency:
            user_currency[str(interaction.user.id)] = 0
        #Check if the user has enough currency to purchase the item      
        if user_currency[str(interaction.user.id)] < item_prices[item]:
            return await interaction.response.send_message("You don't have enough currency for this purchase!", ephemeral=True, delete_after=30)
        #Check if the user is in the purchase history dictionary
        if str(interaction.user.id) not in user_purchase_history:
            user_purchase_history[str(interaction.user.id)] = {}
        #Check if the user has already purchased the maximum number of items for the month and continue
        if item not in user_purchase_history[str(interaction.user.id)]:
            user_purchase_history[str(interaction.user.id)][item] = 0
        #Check if the user has already purchased the maximum number of items for the month 
        if user_purchase_history[str(interaction.user.id)][item] >= user_role['limits'][item]:
            return await interaction.response.send_message("You have reached the maximum number of purchases for this item this month!", ephemeral=True, delete_after=30)

        #Open the modal for the user to enter their Ingame ID
        modal = IngameIDModal(interaction, item)
        await interaction.response.send_modal(modal)

#setpatreonmoney
@bot.slash_command(guild_ids=[guild_id])
async def setpatreonmoney(interaction: nextcord.Interaction, member_id: nextcord.User = SlashOption(name="member_id", required=True), role: nextcord.Role = SlashOption(name='member_role', required=True), amount: int = SlashOption(name='amount', required=True, min_value=0,max_value=16)):
    setpatreonmoney_amount = amount
    setpatreonmoney_memberID = member_id.id
    setpatreonmoney_role = role.id

    if any(r.name in allowed_roles for r in interaction.user.roles):
        if str(setpatreonmoney_role) in role_details and 0 <= amount <= role_details[str(setpatreonmoney_role)]['currency']:
            user_currency[str(member_id.id)] = setpatreonmoney_amount
            with open('user_currency.json', 'r') as f:
                data = json.load(f)
            data[str(member_id.id)] = setpatreonmoney_amount
            with open('user_currency.json', 'w') as f:
                json.dump(data, f)

            #Retrieve the role name
            role_name = role_details[str(setpatreonmoney_role)]['name']

            channel = bot.get_channel(log_channel_id)
            embed = nextcord.Embed(title="Set Patreon Money Log", description=f"{interaction.user.mention} has set {member_id.mention}'s `[{role_name}]` currency to `{setpatreonmoney_amount}` for this month.", color=0x00ff00)
            await channel.send(embed=embed)
            await interaction.response.send_message(f"{member_id.mention}'s `[{role_name}]` currency has been set to `{setpatreonmoney_amount}` for this month.", ephemeral=True, delete_after=30)
        else:
            await interaction.response.send_message("Invalid role or amount.", ephemeral=True, delete_after=30)
    else:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True, delete_after=30)

#setpatreonlimit
@bot.slash_command(guild_ids=[guild_id])
async def setpatreonlimit(interaction: nextcord.Interaction, member_id: nextcord.User = SlashOption(name="member_id", required=True), item: str = SlashOption(name='item', required=True, choices={'Reskin', 'Regender', 'Retalent'}), limit: int = SlashOption(name='limit', required=True, min_value=0)):
    
    if any(r.name in allowed_roles for r in interaction.user.roles):
        if str(member_id.id) in user_purchase_history and item in user_purchase_history[str(member_id.id)]:
            user_purchase_history[str(member_id.id)][item] = limit
            with open('user_purchase_history.json', 'r') as f:
                data = json.load(f)
            data[str(member_id.id)][item] = limit
            with open('user_purchase_history.json', 'w') as f:
                json.dump(data, f)

            #Retrieve the role name
            user_role = [role for role in member_id.roles if str(role.id) in role_details]
            role_name = role_details[str(user_role[0].id)]['name'] if user_role else "No Patreon Role"

            channel = bot.get_channel(log_channel_id)
            embed = nextcord.Embed(title="Set Patreon Limit Log", description=f"{interaction.user.mention} has set {member_id.mention}'s ({role_name}) limit for `{item}` to {limit} for this month.", color=0x00ff00)
            await channel.send(embed=embed)
            await interaction.response.send_message(f"{member_id.mention}'s ({role_name}) limit for `{item}` has been set to {limit} for this month.", ephemeral=True, delete_after=30)
        else:
            await interaction.response.send_message("Invalid member ID or item.", ephemeral=True, delete_after=30)
    else:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True, delete_after=30)

#viewpatreonadmin
@bot.slash_command(guild_ids=[guild_id])
async def viewpatreonadmin(interaction: nextcord.Interaction, member_id: nextcord.User = SlashOption(name="member_id", required=True)):
    
    if any(r.name in allowed_roles for r in interaction.user.roles):
        if str(member_id.id) in user_currency:
            #Retrieve the role name and details
            user_role = [role for role in member_id.roles if str(role.id) in role_details]
            user_role_details = role_details[str(user_role[0].id)] if user_role else None
            
            #Get the currency and purchase history
            currency = user_currency[str(member_id.id)]
            purchase_history = user_purchase_history.get(str(member_id.id), {})

            #Calculate the remaining purchases for each item
            remaining_purchases = {item: user_role_details['limits'][item] - purchase_history.get(item, 0) for item in ["Reskin", "Regender", "Retalent"]}

            #Format the remaining purchases for the message
            remaining_purchases_text = "\n".join(f"{item}: `{count}`" for item, count in remaining_purchases.items())

            #Create the embed message
            embed = nextcord.Embed(title="Patreon Status", description=f"{member_id.mention} `{user_role_details['name']}`\n\nCurrency: `{currency}`\n\nRemaining Purchases:\n{remaining_purchases_text}")
            await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=30)
        else:
            await interaction.response.send_message("Invalid member ID.", ephemeral=True, delete_after=30)
    else:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True, delete_after=30)

#viewpatreon
@bot.slash_command(guild_ids=[guild_id])
async def viewpatreon(interaction: nextcord.Interaction):
    if str(interaction.user.id) in user_currency:
        #Retrieve the role name and details
        user_role = [role for role in interaction.user.roles if str(role.id) in role_details]
        user_role_details = role_details[str(user_role[0].id)] if user_role else None
        
        # If user does not have a qualifying role, return a message
        if user_role_details is None:
            return await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True, delete_after=30)
        
        #Get the currency and purchase history
        currency = user_currency[str(interaction.user.id)]
        purchase_history = user_purchase_history.get(str(interaction.user.id), {})

        #Calculate the remaining purchases for each item
        remaining_purchases = {item: user_role_details['limits'][item] - purchase_history.get(item, 0) for item in ["Reskin", "Regender", "Retalent"]}

        #Format the remaining purchases for the message
        remaining_purchases_text = "\n".join(f"{item}: `{count}`" for item, count in remaining_purchases.items())

        #Create the embed message
        embed = nextcord.Embed(title="Patreon Status", description=f"{interaction.user.mention} `{user_role_details['name']}`\n\nCurrency: `{currency}`\n\nRemaining Purchases:\n{remaining_purchases_text}")
        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=30)
    else:
        await interaction.response.send_message("You do not have any Patreon currency or limits.", ephemeral=True, delete_after=30)

#Event Ready
@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    patreon_shop_channel = bot.get_channel(patreon_shop_channel_id)
    await patreon_shop_channel.purge(limit=None)

    # Load the shop message from the JSON file
    with open('shop_message.json', 'r') as file:
        data = json.load(file)

    embed_title = data['title']
    shop_message = data['message']
    footnote = data['footnote']

    embed = nextcord.Embed(title=embed_title, color=0xFFD700)  # Gold gelb
    embed.add_field(name="Welcome to the Deep Abyss Patreon Shop!", value=shop_message, inline=False)
    embed.set_footer(text=footnote)

    await patreon_shop_channel.send(embed=embed, view=ShopView())

    reset_currency.start()
    reset_purchase_history.start()

bot.run(TOKEN)
