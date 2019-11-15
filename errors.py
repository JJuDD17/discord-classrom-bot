from discord.ext import commands


class StudentStringToIdConversionError(commands.CommandError):
    def __init__(self, message):
        self.message = message


class MissingFile(commands.CommandError):
    def __init__(self, file_description):
        self.file_description = file_description


class NoSuchTaskId(commands.CommandError):
    pass


class MissingMark(commands.CommandError):
    def __init__(self, task_id, student_id):
        self.task_id = task_id
        self.student_id = student_id
