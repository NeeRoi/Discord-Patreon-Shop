import nextcord
from nextcord.ext import commands, tasks
from nextcord import ui, interactions, SlashOption, Member, Role
from nextcord.ui import button, View, Modal
from nextcord import Embed, Button, ButtonStyle, ActionRow
import os
import json
import datetime
import re
from datetime import datetime, timedelta
from config import TOKEN

intents = nextcord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)

#initialise the role details dictionary
role_details = {
    '1129764767628787742': {
        'name': 'Juvie',
        'currency': 3,
        'limits': {
            'Reskin': 2,
            'Regender': 0,
            'Retalent': 0,
            'Nesting': 1
        }
    },
    '1129764708858200154': {
        'name': 'Sub-Adult',
        'currency': 8,
        'limits': {
            'Reskin': 4,
            'Regender': 1,
            'Retalent': 0,
            'Nesting': 3
        }
    },
    '1129764624468807690': {
        'name': 'Adult',
        'currency': 13,
        'limits': {
            'Reskin': 6,
            'Regender': 2,
            'Retalent': 1,
            'Nesting': 4
        }
    },
    '1129765057597816872': {
        'name': 'Elder',
        'currency': 21,
        'limits': {
            'Reskin': 9,
            'Regender': 4,
            'Retalent': 3,
            'Nesting': 5
        }
    }
}

item_prices = {
    'Reskin': 1,
    'Regender': 1,
    'Retalent': 1,
    'Nesting': 1
}

#Set the channel/server IDs
patreon_shop_channel_id = 1129094664625074197
patreon_request_channel_id = 1129094520710111282
log_channel_id = 1129760990360240239
guild_id = 1129093489670500422 #server id
shop_request_id = 1134234390071873597
nesting_request_id = 1134569393565737141

#allowed_roles = ["Staff", "Admin", "Moderator", "Developer", "Owner"] aktuell nur staff
allowed_roles = [1132058617563070484]

#Staff role
staff_role_id = 1129093774623117354
tech_role_id = 235483154847236096

#Initialisiere the Currency and Purchase History dictionaries
user_currency = {}
user_purchase_history = {}

#load the currency and purchase history JSON files
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
    #Get the current time in UTC
    now_utc = datetime.utcnow()
    #Convert to UTC-7
    now_pacific = now_utc - timedelta(hours=7)
    #print("Checking if 5 mins are up 'Resetting currency'")
    #if datetime.now().minute % 5 == 0:
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
    #Get the current time in UTC
    now_utc = datetime.utcnow()
    #Convert to UTC-7
    now_pacific = now_utc - timedelta(hours=7)
    #print("Checking if 5 mins are up 'Resetting limit'")
    #if datetime.now().minute % 5 == 0:
    if now_pacific.day == 1 and now_pacific.hour == 1 and now_pacific.minute == 1: #Check if it's the first day of the month and if the time is 01:00
        user_purchase_history = {}
        print("Resetting purchase history")
        with open('user_purchase_history.json', 'w') as f:
            json.dump(user_purchase_history, f)


#Specify the modal and the input
class IngameIDModal(nextcord.ui.Modal):
    def __init__(self, ctx, item):
        super().__init__(title="Enter Ingame-ID!", timeout=None)
        self.ctx = ctx
        self.item = item
        self.ingame_id = None 

        #Add a text input field for the Ingame ID
        self.IngID = nextcord.ui.TextInput(label="Ingame-ID", placeholder="Enter Ingame-ID!", required=True, custom_id="ingame_id")
        self.add_item(self.IngID)

    #Starts after the modal closes
    async def callback(self, interaction: nextcord.Interaction):
        self.ingame_id = self.IngID.value 
        if self.ingame_id.isnumeric() and len(self.ingame_id) in range(3, 5):
            #Create embed message
            embed = Embed(title="Patreon Shop Request", description=f"{interaction.user.mention} has `{self.item}` purchased. Their Ingame-ID is `{self.ingame_id}`. Please confirm or cancel the request!", color=0xFFFF00)
            
            #Initialize the UserView first
            user_view = UserView(interaction.user, self.item, self.ingame_id)
            user_embed = Embed(title="Patreon Shop Request", description=f"Your purchase of `{self.item}` was successfully requested. Their Ingame-ID is `{self.ingame_id}`. Please wait until a staff member confirms your request.", color=0xFFFF00)
            try:
                if user_view.user_message is not None:
                    await user_view.user_message.edit(embed=user_embed, view=user_view)
                else:
                    user_view.user_message = await interaction.user.send(embed=user_embed, view=user_view)
            except nextcord.errors.Forbidden:
                await interaction.channel.send(f"{interaction.user.mention}, I could not send you a direct message. Please check your privacy settings and try again.", delete_after=60)

            #Then initialize the CustomView
            view = CustomView(interaction.user, self.item, self.ingame_id, None, user_view)
            user_view.set_patreon_view(view) 

            #Send the request to the Patreon request channel and ping the staff role
            patreon_request_channel = self.ctx.guild.get_channel(patreon_request_channel_id)
            patreon_message = await patreon_request_channel.send(content=f"<@&{staff_role_id}>",embed=embed, view=view) 

            #Update the patreon_message in the CustomView
            view.patreon_message = patreon_message
        
            #Close the modal and send an ephemeral message to the user
            return await interaction.response.send_message(f"Your purchase of `{self.item}` was successfully requested. Their Ingame-ID is `{self.ingame_id}`. Please wait until a staff member confirms your request.", ephemeral=True, delete_after=60)
        else:
            #Send an ephemeral message to the user indicating that the Ingame ID is invalid
            return await interaction.response.send_message("Invalid Ingame-ID. Please enter a 3-4 digit number.", ephemeral=True, delete_after=60)

#Creating Patreon channel Buttons
class CustomView(nextcord.ui.View):
    def __init__(self, user: nextcord.User, item: str, ingame_id: str, patreon_message: nextcord.Message, user_view: nextcord.ui.View = None):
        super().__init__(timeout=None)
        self.user = user
        self.item = item
        self.ingame_id = ingame_id
        self.patreon_message = patreon_message
        self.user_view = user_view

    @nextcord.ui.button(label="Confirm Request", style=nextcord.ButtonStyle.green)
    async def confirm_order(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        #Update the embed of the Patreon channel's message
        new_embed = Embed(title="Request Confirmed", description=f"{self.user.mention} purchase of `{self.item}` has been completed! Their Ingame-ID is `{self.ingame_id}`.\n\nThis request has been completed by {interaction.user.mention}.", color=0x7CFC00)  #Create a new embed with the confirmation message
        await self.patreon_message.edit(embed=new_embed, view=None)
        await interaction.response.send_message(f"Successfully completed the patreon shop request for {self.user.mention}, for {self.item}.", ephemeral=True)
        #Update user's currency
        user_currency[str(self.user.id)] -= item_prices[self.item]
        with open('user_currency.json', 'w') as f:
            json.dump(user_currency, f)

        #Update user's purchase history
        user_purchase_history[str(self.user.id)][self.item] += 1
        with open('user_purchase_history.json', 'w') as f:
            json.dump(user_purchase_history, f)

        #Update the user's message
        new_user_embed = Embed(title="Request Confirmed", description=f"Your purchase of `{self.item}` has been completed! Your Ingame-ID is `{self.ingame_id}`.\n\nIf your request has not been completed within 5 minutes after receiving this message, please contact our Support Bot!", color=0x7CFC00)  #Create a new embed with the confirmation message
        if self.user_view.user_message is not None: 
            try:
                await self.user_view.user_message.edit(embed=new_user_embed, view=None)
            except nextcord.errors.Forbidden:
                patreon_shop_channel = bot.get_channel(patreon_shop_channel_id)
                await patreon_shop_channel.send(f"{self.user.mention}, I could not send you a direct message. Please check your privacy settings and try again.", delete_after=60)
        else:
            patreon_shop_channel = bot.get_channel(patreon_shop_channel_id)
            await patreon_shop_channel.send(f"{self.user.mention}, Your Request has been confirmed and will be processed shortly.\n\nIf your request has not been completed within 5 minutes after receiving this message, please contact our Support Bot!", delete_after=60)

    @nextcord.ui.button(label="Request Cancelled", style=nextcord.ButtonStyle.red)
    async def cancel_order(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        #Update the embed of the Patreon channel's message
        new_embed = Embed(title="Request Cancelled", description=f"{self.user.mention} purchase of `{self.item}` has been canceled! Their Ingame-ID is `{self.ingame_id}`.\n\nThis request has been cancelled by {interaction.user.mention}.", color=0xFF0000)  #Create a new embed with the cancellation message
        await self.patreon_message.edit(embed=new_embed, view=None)  #Edit the original message's embed
        await interaction.response.send_message(f"Successfully cancelled the patreon shop request for {self.user.mention}, for {self.item}.", ephemeral=True)

        #Update the user's message
        new_user_embed = Embed(title="Request Cancelled", description=f"Your purchase of `{self.item}` has been canceled!\n\nIf you did not receive a refund for your request please contact the Support Bot!", color=0xFF0000)  #Create a new embed with the cancellation message
        try:
            if self.user_view.user_message is not None:
                await self.user_view.user_message.edit(embed=new_user_embed, view=None)
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
        super().__init__(timeout=None)
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

        #Update the Patreon message
        new_patreon_embed = Embed(title="Request Cancelled", description=f"{self.user.mention}'s purchase of `{self.item}` has been cancelled! Their Ingame-ID is `{self.ingame_id}`.\n\nThis request has been cancelled by {interaction.user.mention}.", color=0xFF0000)  #Create a new embed with the cancellation message
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

#get_user_currency_and_limit /patreonnesting
def get_user_currency_and_limit(user_id):
    #Open and load the currency and limits JSON files
    with open('user_currency.json', 'r') as f:
        user_currency_data = json.load(f)
    with open('user_purchase_history.json', 'r') as f:
        user_purchase_history_data = json.load(f)

    #Fetch user's currency
    user_currency = user_currency_data.get(str(user_id), 0)

    #Fetch user's purchase history
    user_purchase_history = user_purchase_history_data.get(str(user_id), {})
    print(f"User ID: {user_id}, Currency: {user_currency}, Purchase History: {user_purchase_history}")
    return user_currency, user_purchase_history

#Update the user's currency and limit /patreonnesting
def update_user_currency_and_limit(user_id, new_currency, user_purchase_history):
    with open('user_currency.json', 'r') as f:
        user_currency_data = json.load(f)
    user_currency_data[str(user_id)] = new_currency
    with open('user_currency.json', 'w') as f:
        json.dump(user_currency_data, f)

    with open('user_purchase_history.json', 'r') as f:
        user_purchase_history_data = json.load(f)
    user_purchase_history_data[str(user_id)] = user_purchase_history
    with open('user_purchase_history.json', 'w') as f:
        json.dump(user_purchase_history_data, f)

    print(f"Updating user ID: {user_id}, New Currency: {new_currency}, New Purchase History: {user_purchase_history}")

#Creates the modal for update button /patreonnesting
class UpdateModal(nextcord.ui.Modal):
    def __init__(self, view):
        super().__init__(title="Update Nesting Request", timeout=None)
        self.view = view
        self.text = nextcord.ui.TextInput(label="Update", placeholder="Enter your update here...")
        self.add_item(self.text)
        self.done_button = nextcord.ui.Button(label="Done")
        self.add_item(self.done_button)

    async def callback(self, interaction: nextcord.Interaction):
        embed = self.view.nesting_request_message.embeds[0]
        embed.description += f"\n\nUpdate: {self.text.value}"
        await self.view.nesting_request_message.edit(embed=embed, view=None)

#ConfirmAndCancel View for buttons /patreonnesting
class ConfirmAndCancel(nextcord.ui.View):
    def __init__(self, user_id, interaction: nextcord.Interaction, user_role_detail, nesting_request_message: nextcord.Message, dino: str, build: str, steamid: str, timeavailable: str):
        super().__init__(timeout=None)
        self.user_id = user_id #User ID of the user who created the request
        self.user = interaction.user #User who clicked the button
        self.interaction = interaction 
        self.user_role_detail = user_role_detail #Role details of the user who created the request
        self.nesting_request_message = nesting_request_message #Message of the nesting request
        self.dino = dino
        self.build = build
        self.steamid = steamid
        self.timeavailable = timeavailable

    #Confirm button
    @nextcord.ui.button(label="Confirm", style=nextcord.ButtonStyle.green, row=0)
    async def confirm(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        #Check if the user's role is in the list of allowed roles
        if not any(int(role.id) in allowed_roles for role in interaction.user.roles):
            return await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        user_currency, user_purchase_history = get_user_currency_and_limit(self.user_id)
        user_limit = user_purchase_history.get('Nesting', 0)
        #Check if the user has enough currency to confirm the purchase
        required_currency = 1
        max_limit = self.user_role_detail['limits']['Nesting']
        print(f"User limit: {user_limit}, Max limit: {max_limit}")
        if user_currency < required_currency or user_limit >= max_limit:
            await interaction.response.send_message("You don't have enough currency or limit to confirm this purchase.", ephemeral=True)
            return
        
        #Update the user's currency and purchase history
        user_currency -= required_currency
        user_purchase_history['Nesting'] = user_limit + 1
        update_user_currency_and_limit(self.user_id, user_currency, user_purchase_history)

        #Update the message
        if self.nesting_request_message.embeds:
            embed = self.nesting_request_message.embeds[0]
            embed.color = nextcord.Color.orange()
            embed.description = f"{self.user.mention}'s nesting request for `{self.dino}` ({self.build}) is confirmed. Their Steam ID is `{self.steamid}` and they are available at `{self.timeavailable}`.\n\nThis request has been confirmed by {interaction.user.mention}"
            participation_view = ParticipationView(interaction.user, self.user_id, self.user_role_detail, self.nesting_request_message, self.dino, self.build, self.steamid, self.timeavailable)
            await self.nesting_request_message.edit(embed=embed, view=participation_view)            
            await interaction.response.send_message(f"You confirmed the Nesting Request for {self.user.mention}", ephemeral=True)
            await self.user.send(f"Your nesting request has been Confirmed! Please follow your request in the Patreon Nesting channel. You can check your monthly limits with /viewpatreon, if you not wish to participate in your Nesting please contact the Support Bot!")
    
    #Cancel button
    @nextcord.ui.button(label="Cancel", style=nextcord.ButtonStyle.red, row=0)
    async def cancel(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        #Check if the user's role is in the list of allowed roles
        if not any(int(role.id) in allowed_roles for role in interaction.user.roles):
            return await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        new_embed = nextcord.Embed(title="Request Cancelled", description=f"{self.user.mention}'s nesting request for `{self.dino}` ({self.build}). Their Steam ID is `{self.steamid}` and they are available at `{self.timeavailable}`.This request has been cancelled by {interaction.user.mention}.", color=0xFF0000)
        await self.nesting_request_message.edit(embed=new_embed, view=None)
        await interaction.response.send_message(f"Successfully cancelled the nesting request for {self.user.mention}.", ephemeral=True)

        await self.user.send(f"Your nesting request has been cancelled. You can request a new one in the Patreon Nesting channel. You can check your monthly limits with /viewpatreon, if you did not receive a refund for your request please contact the Support Bot!")

#"Join", "Remove me!", "Update" and "Close" buttons /patreonnesting
class ParticipationView(nextcord.ui.View):
    def __init__(self, user, user_id, user_role_detail, nesting_request_message: nextcord.Message, dino: str, build: str, steamid: str, timeavailable: str):
        super().__init__(timeout=None)
        self.user = user
        self.user_id = user_id
        self.user_role_detail = user_role_detail
        self.nesting_request_message = nesting_request_message
        self.dino = dino
        self.build = build
        self.steamid = steamid
        self.timeavailable = timeavailable
        self.participants = []
        self.last_interaction = None

    def format_participants(self):
        participants_mentions = ', '.join([f'<@{participant_id}>' for participant_id in self.participants])
        return f"The following users are also participating in this nesting:\n{participants_mentions}"
    
    #Join button
    @nextcord.ui.button(label="Join", style=nextcord.ButtonStyle.green, row=1)
    async def participate(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.last_interaction = interaction
        user_role = None
        for role in interaction.user.roles:
            if role.id in [int(id_str) for id_str in role_details.keys()]:
                user_role = role_details[str(role.id)]
        if not user_role:
            return await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)

        #Prevent the buyer from participating
        if interaction.user.id == self.user_id:
            return await interaction.response.send_message("You already participate in your own nesting, if you wish to cancel, message a Admin!", ephemeral=True, delete_after=60)

        #Check if the user is already participating
        if interaction.user.id in self.participants:
            return await interaction.response.send_message("You are already participating in this nesting.", ephemeral=True, delete_after=60)

        user_currency, user_purchase_history = get_user_currency_and_limit(interaction.user.id)
        user_limit = user_purchase_history.get('Nesting', 0)
        required_currency = 1
        max_limit = user_role['limits']['Nesting']

        if user_currency < required_currency or user_limit >= max_limit:
            await interaction.response.send_message("You don't have enough currency or limit to participate.", ephemeral=True, delete_after=60)
        else:
            #If not, add the user to the participants list
            self.participants.append(interaction.user.id)
            user_currency, user_purchase_history = get_user_currency_and_limit(interaction.user.id)
            print(f"User purchase history before update: {user_purchase_history}")
            user_purchase_history['Nesting'] += 1
            user_currency -= 1
            update_user_currency_and_limit(interaction.user.id, user_currency, user_purchase_history)

            #Update the embed description
            embed = self.nesting_request_message.embeds[0]
            description_lines = embed.description.split('\n')

            #Remove the line with the participants if it exists
            description_lines = [line for line in description_lines if "The following users are also participating in this nesting:" not in line]
            #Also remove the line with the first participant
            description_lines = [line for line in description_lines if not (line.startswith('<@') and line.endswith('>'))]

            #Add the new line with the updated participants
            description_lines.append(self.format_participants())

            new_description = '\n'.join(description_lines)
            embed.description = new_description
            await self.nesting_request_message.edit(embed=embed)

            await interaction.response.send_message("You have successfully joined the nesting.", ephemeral=True, delete_after=60)

    #Remove me! button
    @nextcord.ui.button(label="Remove me!", style=nextcord.ButtonStyle.red, row=1)
    async def dont_participate(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if interaction.user.id not in self.participants:
            return await interaction.response.send_message("You are not participating in this nesting.", ephemeral=True, delete_after=60)

        self.participants.remove(interaction.user.id)
        user_currency, user_purchase_history = get_user_currency_and_limit(interaction.user.id)
        print(f"User purchase history after update: {user_purchase_history}")
        user_purchase_history['Nesting'] -= 1
        user_currency += 1
        update_user_currency_and_limit(interaction.user.id, user_currency, user_purchase_history)
        await interaction.response.send_message("You have successfully left the Patreon Nesting.", ephemeral=True, delete_after=60)

        #Update the embed description
        embed = self.nesting_request_message.embeds[0]
        description_lines = embed.description.split('\n')

        #Remove the line with the participants if it exists
        description_lines = [line for line in description_lines if "The following users are also participating in this nesting:" not in line]
        #Also remove the line with the first participant
        description_lines = [line for line in description_lines if not (line.startswith('<@') and line.endswith('>'))]

        #Add the new line with the updated participants if there are any
        if self.participants:
            description_lines.append(self.format_participants())

        new_description = '\n'.join(description_lines)
        embed.description = new_description
        await self.nesting_request_message.edit(embed=embed)
    
    #Update button
    @nextcord.ui.button(label="Update", style=nextcord.ButtonStyle.grey, row=1)
    async def update(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if not any(role.id in allowed_roles for role in interaction.user.roles):
            return await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True, delete_after=60)

        #Store this interaction as the last update interaction
        self.last_update_interaction = interaction

        #Open the modal
        modal2 = UpdateModal(self)
        await interaction.response.send_modal(modal2)

    async def update_embed(self, update_text=None):
        #Use the last update interaction for the log
        interaction = self.last_update_interaction
        embed = self.nesting_request_message.embeds[0]
        description_lines = embed.description.split('\n')

        #If there was an update, add it to the description
        if update_text:
            description_lines.append(f"\n**Update:** `{update_text}`")

        #Join the lines back into a single string and update the embed description
        embed.description = '\n'.join(description_lines)

        await self.nesting_request_message.edit(embed=embed)
        #Extract all mentions from the embed description
        embed_description = self.nesting_request_message.embeds[0].description
        mentions = re.findall(r'<@\d+>', embed_description)

        #Send an update message to the channel and ping all users
        update_message = "The nesting request has been updated!\n"
        update_message += ' '.join(mentions)
        await interaction.channel.send(update_message)

        #Get the log channel
        log_channel = bot.get_channel(log_channel_id)
        #Send a log message
        await log_channel.send(f"{interaction.user.mention} has updated a nesting request!\nDetails of the request: {description_lines[0]}\nUpdate: `{update_text}`")

    #Close button
    @nextcord.ui.button(label="Close", style=nextcord.ButtonStyle.grey, row=2)
    async def finished(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.last_interaction = interaction       
        #Check if the user's role is in the list of allowed roles
        if not any(role.id in allowed_roles for role in interaction.user.roles):
            return await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True, delete_after=60)

        #Add the new line to the embed
        embed = self.nesting_request_message.embeds[0]
        embed.color = nextcord.Color.green()
        embed.description += f"\nNesting in progress or finished, confirmed by {interaction.user.mention}!"
        await self.nesting_request_message.edit(embed=embed)

        #Disable all the buttons
        for item in self.children:
            item.disabled = True
        await self.nesting_request_message.edit(view=self)

        await interaction.response.send_message("The nesting has been marked as finished.", ephemeral=True, delete_after=60)

#Creating UpdateModal for update button /patreonnesting
class UpdateModal(nextcord.ui.Modal):
    def __init__(self, view):
        super().__init__(title="Enter Ingame-ID!", timeout=None)
        self.text = nextcord.ui.TextInput(label="Update", placeholder="Enter Update information for participations", required=True, custom_id="Input Text")
        self.add_item(self.text)
        self.view = view        
    #Actions after modal is closed
    async def callback(self, interaction: nextcord.Interaction):
        await self.view.update_embed(self.text.value)
        await interaction.response.send_message("Nesting request has been updated!", ephemeral=True, delete_after=30)

#/patreonnesting Command
@bot.slash_command(guild_ids=[guild_id])
async def patreonnesting(
    interaction: nextcord.Interaction, 
    dino: str = SlashOption(name='dino', description='Choose your desired dino', required=True, choices={'Rex', 'Acro', 'Megar', 'Wiehen', 'Velo', 'Apa', 'Para', 'Sai', 'Lurdu', 'Ory', 'Coah', 'Pachy', 'Elasmo', 'Mosa', 'Krono', 'Ptera', 'Trope'}),
    build: str = SlashOption(name='build', description='Choose your desired build', required=True, choices={'Speed/Combat', 'Speed/Surv', 'Surv/Combat', 'Speed/Combat/Surv'}),
    steamid: str = SlashOption(name='steamid', description='Enter your Steam ID', required=True, min_length=17, max_length=17),
    timeavailable: str = SlashOption(name='timeavailable', description='Enter desired Date, Time and Timezone!', required=True)
):
    #Get the user's role
    user_role = None
    for role in interaction.user.roles:
        if str(role.id) in role_details:
            user_role = role_details[str(role.id)]
    if not user_role:
        return await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True, delete_after=30)
    
    #Check if the user has enough currency to purchase the item 
    user_currency, user_purchase_history = get_user_currency_and_limit(interaction.user.id)
    if user_currency < 1: #price of the command is 1
        return await interaction.response.send_message("You don't have enough currency for this purchase!", ephemeral=True, delete_after=30)
    
    #Check if the user has already purchased the maximum number of items for the month
    user_limit = user_purchase_history.get('Nesting', 0)
    if user_limit >= user_role['limits']['Nesting']:
        return await interaction.response.send_message("You have reached the maximum number of purchases for this item this month!", ephemeral=True, delete_after=30)

    nesting_request_channel = bot.get_channel(nesting_request_id)
    await nesting_request_channel.send(f"<@&{staff_role_id}>")    
    view = ConfirmAndCancel(interaction.user.id, interaction, user_role, None, dino, build, steamid, timeavailable) 
    embed = nextcord.Embed(title="Nesting Request", description=f"{interaction.user.mention}'s nesting request for `{dino}` ({build}) is pending. Their Steam ID is `{steamid}` and they are available at `{timeavailable}`.\n\nPlease confirm or cancel this request.", color=0xFFFF00)
    message = await nesting_request_channel.send(embed=embed, view=view)
    view.nesting_request_message = message
    await interaction.response.send_message("Your Request will be soon overlooked!", ephemeral=True, delete_after=60)

#setpatreonmoney
@bot.slash_command(guild_ids=[guild_id])
async def setpatreonmoney(interaction: nextcord.Interaction, member_id: nextcord.User = SlashOption(name="member_id", required=True), role: nextcord.Role = SlashOption(name='member_role', required=True), amount: int = SlashOption(name='amount', required=True, min_value=0,max_value=21)):
    setpatreonmoney_amount = amount
    setpatreonmoney_memberID = member_id.id
    setpatreonmoney_role = role.id

    if any(int(r.id) in allowed_roles for r in interaction.user.roles):
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
async def setpatreonlimit(interaction: nextcord.Interaction, member_id: nextcord.User = SlashOption(name="member_id", required=True), item: str = SlashOption(name='item', required=True, choices={'Reskin', 'Regender', 'Retalent', 'Nesting'}), limit: int = SlashOption(name='limit', required=True, min_value=0, max_value=9)):
    
    if any(int(r.id) in allowed_roles for r in interaction.user.roles):
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
            embed = nextcord.Embed(title="Set Patreon Limit Log", description=f"{interaction.user.mention} has set {member_id.mention}'s `[{role_name}]` limit for `{item}` to {limit} for this month.", color=0x00ff00)
            await channel.send(embed=embed)
            await interaction.response.send_message(f"{member_id.mention}'s `[{role_name}]` limit for `{item}` has been set to {limit} for this month.", ephemeral=True, delete_after=30)
        else:
            await interaction.response.send_message("Invalid member ID or item.", ephemeral=True, delete_after=30)
    else:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True, delete_after=30)

#viewpatreonadmin
@bot.slash_command(guild_ids=[guild_id])
async def viewpatreonadmin(interaction: nextcord.Interaction, member_id: nextcord.User = SlashOption(name="member_id", required=True)):
    
    if any(int(r.id) in allowed_roles for r in interaction.user.roles):
        #Get the currency and purchase history
        currency, purchase_history = get_user_currency_and_limit(member_id.id)

        if currency is not None:
            #Retrieve the role name and details
            user_role = [role for role in member_id.roles if str(role.id) in role_details]
            user_role_details = role_details[str(user_role[0].id)] if user_role else None
            
            #Calculate the remaining purchases for each item
            remaining_purchases = {item: user_role_details['limits'][item] - purchase_history.get(item, 0) for item in ["Reskin", "Regender", "Retalent", "Nesting"]}

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
    #Get the currency and purchase history
    currency, purchase_history = get_user_currency_and_limit(interaction.user.id)

    if currency is not None:
        #Retrieve the role name and details
        user_role = [role for role in interaction.user.roles if str(role.id) in role_details]
        user_role_details = role_details[str(user_role[0].id)] if user_role else None
        
        #If user does not have a qualifying role, return a message
        if user_role_details is None:
            return await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True, delete_after=30)

        #Calculate the remaining purchases for each item
        remaining_purchases = {item: user_role_details['limits'][item] - purchase_history.get(item, 0) for item in ["Reskin", "Regender", "Retalent", "Nesting"]}

        #Format the remaining purchases for the message
        remaining_purchases_text = "\n".join(f"{item}: `{count}`" for item, count in remaining_purchases.items())

        #Create the embed message
        embed = nextcord.Embed(title="Patreon Status", description=f"{interaction.user.mention} `{user_role_details['name']}`\n\nCurrency: `{currency}`\n\nRemaining Purchases:\n{remaining_purchases_text}")
        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=30)
    else:
        await interaction.response.send_message("You do not have any Patreon currency or limits.", ephemeral=True, delete_after=30)


##############RandomStormTimer ##############
class RandomStorm:
    def __init__(self, bot):
        self.bot = bot
        self.last_message_time = datetime.utcnow()

    async def initialize_last_message_time(self):
        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                if channel.id == shop_request_id:
                    async for message in channel.history(limit=100):
                        for embed in message.embeds:
                            if 'purchase of Random Storm for $200,000 has been completed!' in embed.description:
                                self.last_message_time = message.created_at.replace(tzinfo=None)
                                return

    async def on_message(self, message):
        #print("Received a message.")
        if message.channel.id == shop_request_id:
            for embed in message.embeds:
                if 'has purchased Random Storm for $200,000. Their in-game ID is' in embed.description:
                    await self.initialize_last_message_time()
                    next_storm_time, time_difference = self.calculate_next_randomstorm()
                    if time_difference > timedelta(hours=5):
                        embed = nextcord.Embed(title="Random Storm Update", description=f"The last Random Storm was before `{self.format_timedelta(time_difference)}`. \n\nRandom Storm doesn't have a cooldown right now and is available!", color=0x00ff00) #Green embed
                        await message.channel.send(embed=embed)
                    else:
                        remaining_time = timedelta(hours=5) - time_difference
                        embed = nextcord.Embed(title="Random Storm Update", description=f"The last Random Storm was before `{self.format_timedelta(time_difference)}`. \n\nThe Next Random Storm is in `{self.format_timedelta(remaining_time)}` available!", color=0xff0000) #Red embed
                        await message.channel.send(embed=embed)

    async def stormtimer(self, interaction: nextcord.Interaction):    
        #Read the last message time before calculating the time until the next randomstorm
        await self.initialize_last_message_time()

        next_storm_time, time_difference = self.calculate_next_randomstorm()
        if time_difference > timedelta(hours=5):
            embed = nextcord.Embed(title="Random Storm Update", description=f"The last Random Storm was before `{self.format_timedelta(time_difference)}`. \n\nRandom Storm doesn't have a cooldown right now and is available!", color=0x00ff00) #Green embed
            await interaction.response.send_message(embed=embed)
        else:
            remaining_time = timedelta(hours=5) - time_difference
            embed = nextcord.Embed(title="Random Storm Update", description=f"The last Random Storm was before `{self.format_timedelta(time_difference)}`. \n\nThe Next Random Storm is in `{self.format_timedelta(remaining_time)}` available!", color=0xff0000) #Red embed
            await interaction.response.send_message(embed=embed)

    async def testtimer(self, interaction: nextcord.Interaction, *, message: str):
        channel = self.bot.get_channel(shop_request_id)
        embed = nextcord.Embed(description=message)
        await channel.send(embed=embed)
        await interaction.response.send_message('Test message sent!')

    def calculate_next_randomstorm(self):
        if self.last_message_time is None:
            #Handle the case where last_message_time is None
            print("last_message_time is None")
            return None, None
        now = datetime.utcnow()
        time_difference = now - self.last_message_time
        next_storm_time = self.last_message_time + timedelta(hours=5)
        return next_storm_time, time_difference

    def format_timedelta(self, td):
        hours, remainder = divmod(td.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}h:{minutes:02}m:{seconds:02}s"

random_storm = RandomStorm(bot)

@bot.event
async def on_message(message):
    await random_storm.on_message(message)
    await bot.process_commands(message)

@bot.slash_command(guild_ids=[guild_id])
@commands.has_role(staff_role_id)
async def stormtimer(interaction: nextcord.Interaction):    
    await random_storm.stormtimer(interaction)

@bot.slash_command(name="testtimer", description="Send a test embed message")
@commands.has_role(tech_role_id)
async def testtimer(interaction: nextcord.Interaction, message: str = nextcord.SlashOption(name="message", description="Message to send", required=True)):
    await random_storm.testtimer(interaction, message=message)

random_storm = RandomStorm(bot)

#Event Ready
@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    patreon_shop_channel = bot.get_channel(patreon_shop_channel_id)
    await patreon_shop_channel.purge(limit=None)

    #Load the shop message from the JSON file
    with open('shop_message.json', 'r') as file:
        data = json.load(file)

    embed_title = data['title']
    shop_message = data['message']
    footnote = data['footnote']

    embed = nextcord.Embed(title=embed_title, color=0xFFD700)  #gold embed
    embed.add_field(name="Welcome to the Deep Abyss Patreon Shop!", value=shop_message, inline=False)
    embed.set_footer(text=footnote)

    await patreon_shop_channel.send(embed=embed, view=ShopView())
    await random_storm.initialize_last_message_time()

    reset_currency.start()
    reset_purchase_history.start()

bot.run(TOKEN)
