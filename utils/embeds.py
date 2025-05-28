import discord

class EmbedBuilder:
    """Easy embed creation class"""
    
    def __init__(self, title=None, description=None, color=discord.Color.blue()):
        self.embed = discord.Embed(title=title, description=description, color=color)
    
    def set_title(self, title):
        self.embed.title = title
        return self
    
    def set_description(self, description):
        self.embed.description = description
        return self
    
    def set_color(self, color):
        self.embed.color = color
        return self
    
    def add_field(self, name, value, inline=True):
        self.embed.add_field(name=name, value=value, inline=inline)
        return self
    
    def set_footer(self, text, icon_url=None):
        self.embed.set_footer(text=text, icon_url=icon_url)
        return self
    
    def set_author(self, name, icon_url=None, url=None):
        self.embed.set_author(name=name, icon_url=icon_url, url=url)
        return self
    
    def set_thumbnail(self, url):
        self.embed.set_thumbnail(url=url)
        return self
    
    def set_image(self, url):
        self.embed.set_image(url=url)
        return self
    
    def build(self):
        return self.embed
