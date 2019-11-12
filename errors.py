from discord.ext import commands


class StudentStringToIdConversionError(commands.CommandError):
    def __init__(self, message):
        self.message = message


class MissingFile(commands.CommandError):
    def __init__(self, file_description):
        self.file_description = file_description


class NoSuchTaskId(commands.CommandError):
    pass
