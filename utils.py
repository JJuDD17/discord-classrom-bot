from errors import *
import database
import discord
from discord.ext import commands
import os


def get_token(parser):
    environment_token = os.environ.get('DISCORD_BOT_TOKEN', default=None)
    argument_token = parser.parse_args().token
    if not argument_token:
        return environment_token
    return argument_token


async def get_file_from_message(message: discord.Message):
    attachment = message.attachments[0]
    return await attachment.read(), attachment.filename


async def student_string_to_id(ctx: commands.context.Context, student: str):
    if student.startswith('<@') and student.endswith('>'):
        return int(student[2:-1])
    if '#' not in student:
        result = [i for i in discord.utils.get(ctx.guild.members, name=student) if has_role(i, 'pupil')]
        if result:
            if len(result) == 1:
                return result[0].id
            else:
                raise StudentStringToIdConversionError(
                  'Есть несколько учеников с таким ником. Укажите ник с дискриминатором (четыре цифры после ника и #)')
        else:
            raise StudentStringToIdConversionError('Нету учеников с таким ником.')
    else:
        name, discriminator = student.split('#')
        result = [i for i in discord.utils.get(ctx.guild.members, name=name, discriminator=discriminator)
                  if has_role(i, 'pupil')]
        if result:
            return result[0].id
        else:
            raise StudentStringToIdConversionError(
                'Нету учеников с таким ником и дискриминатором (четыре цифры после ника и #).')


def has_role(member, role_string):
    return discord.utils.get(member.guild.roles, name=role_string) in member.roles


def file_required(file_description):
    def predicate(ctx):
        if not ctx.message.attachments:
            raise MissingFile(file_description)
        return True
    return commands.check(predicate)


async def get_undone_tasks(student_id):
    tasks_done = set(await database.tasks_done(student_id))
    all_tasks = set(await database.all_task_ids())
    if len(tasks_done) != len(all_tasks):
        return all_tasks.difference(tasks_done)
    else:
        return set()


async def get_undone_students(task_id, guild_members):
    if task_id not in await database.all_task_ids():
        raise NoSuchTaskId()
    students_done = set([i.id for i in await database.who_has_solution(task_id) if has_role(i, 'pupil')])
    all_students = set([i.id for i in guild_members if has_role(i, 'pupil')])
    if len(students_done) != len(all_students):
        return all_students.difference(students_done)
    else:
        return set()


async def notify(message, guild, role=None, user_id=None, file=None):
    if not role and not user_id:
        return commands.errors.MissingRequiredArgument('user_id')
    if role:
        for member in guild.members:
            if has_role(member, role):
                channel = await member.create_dm()
                await channel.send(message, file=file)
    if user_id:
        members = discord.utils.get(guild.members, id=user_id)
        if not members:
            print(f'no member {user_id} in guild {guild}')
            return
        channel = await members[0].create_dm()
        await channel.send(message, file=file)
