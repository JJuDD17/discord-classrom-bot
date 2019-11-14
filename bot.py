from utils import *
import io
import argparse


MISSING_TOKEN_TEXT = 'Отсутствует токен бота. Вы можете указать его в переменной окружения DISCORD_BOT_TOKEN или ' \
                     'первым аргументом командной строки'
GREETING = '''Добро пожаловать на сервер! Вам автоматически была присвоена роль pupil.
Чтобы посмотреть полный список команд введите !help'''


bot = commands.Bot(command_prefix='!')


#  ---EVENTS---


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await database.init('class.db')


@bot.event
async def on_member_join(member: discord.Member):
    role = discord.utils.get(member.guild.roles, name='pupil')
    await member.add_roles(role)
    channel = await member.create_dm()
    async for message in channel.history(limit=25, oldest_first=True):
        if message.content == GREETING:
            break
    else:
        await channel.send(GREETING)


@bot.event
async def on_command_error(ctx: commands.context.Context, error):
    if isinstance(error, commands.errors.NoPrivateMessage):
        await ctx.send('Эту команду нельзя вызвать через личное сообщение. '
                       'Вызовите команду через один из каналов сервера.')

    if isinstance(error, commands.errors.MissingRole):
        if error.missing_role:
            await ctx.send(f'Вы должны иметь роль {error.missing_role} чтобы использовать эту команду.')

    if isinstance(error, MissingFile):
        await ctx.send(f'Не прикреплен файл, в котором содержится {error.file_description}')

    if isinstance(error, commands.errors.MissingAnyRole):
        await ctx.send('У вас не было роли, теперь вам присвоена роль pupil. Повторите вашу команду.')
        await on_member_join(ctx.message.author)

    if isinstance(error, commands.errors.MissingRequiredArgument):
        await ctx.send('Недостаточно параметров для выполнения команды')

    if isinstance(error, commands.errors.BadArgument):
        await ctx.send('Неправильно введен один из параметров')

    if isinstance(error, StudentStringToIdConversionError):
        await ctx.send(error.message)

    if isinstance(error, NoSuchTaskId):
        await ctx.send('Нет задания с таким номером')


#  ---COMMANDS---


@bot.command(name='add_task', help='Добавить задание')
@commands.guild_only()
@commands.has_role('teacher')
@file_required('задание')
async def add_task(ctx: commands.context.Context, *description):
    if not description:
        description = None
    else:
        description = ' '.join(description)
    file, file_name = await get_file_from_message(ctx.message)
    task_id = await database.add_task(file, file_name, description)
    await ctx.send(f'Задание успешно добавлено. Его номер - {task_id}')
    await notify(f'Появилось новое задание. {description}', ctx.guild, 'pupil', None,
                 discord.File(io.BytesIO(file), filename=file_name))


@bot.command(name='get_task', help='Получить файл задания')
async def get_task(ctx: commands.context.Context, task_id: int):
    result = await database.get_task(task_id)
    if not result:
        await ctx.send('Нет задания с таким номером.')
        return
    file_content, file_name, description = result
    file = discord.File(io.BytesIO(file_content), filename=file_name)
    if description:
        await ctx.send(description, file=file)
    else:
        await ctx.send(f'Задание №{task_id}', file=file)


@bot.command(name='add_solution', help='Загрузить решение задания')
@commands.has_role('pupil')
@file_required('решение')
async def add_solution(ctx: commands.context.Context, task_id: int):
    if task_id in await database.all_task_ids():
        file, file_name = await get_file_from_message(ctx.message)
        await database.add_solution(ctx.message.author.id, task_id, file, file_name)
        await ctx.send('Решение успешно добавлено.')
        await notify(f'Ученик {ctx.message.author.name} решил задание №{task_id}.', ctx.guild, 'teacher', None,
                     discord.File(io.BytesIO(file), filename=file_name))
    else:
        raise NoSuchTaskId()


@bot.command(name='get_solution', help='Получить файл решения')
@commands.guild_only()
@commands.has_any_role()
async def get_solution(ctx: commands.context.Context, task_id: int, student: str = ''):
    if has_role(ctx.message.author, 'teacher'):
        if student:
            student_id = student_string_to_id(ctx, student)
        else:
            raise commands.errors.MissingRequiredArgument('student: str')
    elif has_role(ctx.message.author, 'pupil'):
        student_id = ctx.message.author.id
    else:
        return
    if task_id in await database.all_task_ids():
        result = await database.get_solution(task_id, student_id)
        if not result:
            await ctx.send('У ученика нет решения задания с таким номером.')
            return
        file_content, file_name = result
        file = discord.File(io.BytesIO(file_content), filename=file_name)
        await ctx.send(f'Решение задания №{task_id} учеником '
                       f'{discord.utils.get(ctx.guild.members, id=student_id)[0].name}', file=file)
    else:
        raise NoSuchTaskId()


@bot.command(name='undone', help='Список всех нерешенных заданий')
@commands.guild_only()
@commands.has_any_role()
async def undone(ctx: commands.context.Context, task_id_or_student: str = ''):
    if has_role(ctx.message.author, 'teacher'):
        await undone_for_teacher(ctx, task_id_or_student)
    elif has_role(ctx.message.author, 'pupil'):
        await undone_for_pupil(ctx)


async def undone_for_teacher(ctx: commands.context.Context, task_id_or_student: str = ''):
    try:
        task_id = int(task_id_or_student)
    except ValueError:
        task_id = None

    if task_id:
        undone_students = await get_undone_students(task_id, ctx.message.author.guild.members)
        if undone_students:
            await ctx.send(f'Задание {task_id} не сделали: ' + ', '.join([f'<@{i}>' for i in undone_students]))
        else:
            await ctx.send(f'Задание {task_id} сделали все ученики')
    else:
        student_id = student_string_to_id(ctx, task_id_or_student)
        undone_tasks = await get_undone_tasks(student_id)
        if undone_tasks:
            await ctx.send(f'Ученик <@{student_id}> не сделал задания: ' + ', '.join([str(i) for i in undone_tasks]))
        else:
            await ctx.send(f'Ученик <@{student_id}> сделал все задания')


async def undone_for_pupil(ctx: commands.context.Context):
    student_id = ctx.message.author.id
    undone_tasks = await get_undone_tasks(student_id)
    if undone_tasks:
        await ctx.send(f'Вы не сделали задания: ' + ', '.join([str(i) for i in undone_tasks]))
    else:
        await ctx.send(f'Вы сделали все задания')


@bot.command(name='add_mark', help='Поставить ученику оценку')
@commands.guild_only()
@commands.has_role('teacher')
async def add_mark(ctx: commands.context.Context, mark: int, task_id: int, student: str):
    if task_id not in database.all_task_ids():
        raise NoSuchTaskId()
    student_id = student_string_to_id(ctx, student)
    await database.add_mark(mark, task_id, student_id)
    await notify(f'Вы получили оценку {mark} за задание {task_id}.', ctx.guild, user_id=student_id)


@bot.command(name='get_mark', help='Посмотреть оценку')
@commands.guild_only()
@commands.has_any_role()
async def get_mark(ctx: commands.context.Context, task_id: int, student: str = ''):
    if task_id not in database.all_task_ids():
        raise NoSuchTaskId()
    if has_role(ctx.message.author, 'teacher'):
        student_id = student_string_to_id(ctx, student)
        await ctx.send(await database.get_mark(task_id, student_id))
    elif has_role(ctx.message.author, 'pupil'):
        await ctx.send(await database.get_mark(task_id, ctx.message.author.id))


@bot.command(name='get_marks', help='Посмотреть все оценки')
@commands.guild_only()
@commands.has_any_role()
async def get_marks(ctx: commands.context.Context, student: str = ''):
    if has_role(ctx.message.author, 'teacher'):
        student_id = student_string_to_id(ctx, student)
        await ctx.send(', '.join(await database.get_marks(student_id)))
    elif has_role(ctx.message.author, 'pupil'):
        await ctx.send(', '.join(await database.get_marks(ctx.message.author.id)))


@bot.command(name='average_mark', help='Средняя оценка')
@commands.guild_only()
@commands.has_any_role()
async def average_mark(ctx: commands.context.Context, student: str = ''):
    if has_role(ctx.message.author, 'teacher'):
        student_id = student_string_to_id(ctx, student)
        marks = await database.get_marks(student_id)
        await ctx.send(', '.join(sum(marks) / len(marks)))
    elif has_role(ctx.message.author, 'pupil'):
        marks = await database.get_marks(ctx.message.author.id)
        await ctx.send(', '.join(sum(marks) / len(marks)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('token', default=None, nargs='?',
                        help='token of your discord bot, also can be set in environment variable DISCORD_BOT_TOKEN')
    token = get_token(parser)
    if token:
        bot.run(token)
    else:
        print(MISSING_TOKEN_TEXT)


'''@bot.command(name='old_undone', help='Список всех нерешенных заданий')
@commands.has_any_role()
@commands.guild_only()
async def get_undone_tasks_old(ctx: commands.context.Context, task_id_or_student: str = ''):
    try:
        task_id = int(task_id_or_student)
    except ValueError:
        task_id = None
    if has_role(ctx.message.author, 'teacher'):
        if not task_id:
            raise commands.errors.MissingRequiredArgument('task_id')
        students_done = set([i.id for i in await database.who_has_solution(task_id) if has_role(i, 'pupil')])
        all_students = set([i.id for i in ctx.message.author.guild.members if has_role(i, 'pupil')])
        if len(students_done) != len(all_students):
            students_undone = all_students.difference(students_done)
            await ctx.send(f'Задание №{task_id} не сделали: ' + ', '.join([f'<@{i}>' for i in students_undone]))
        else:
            await ctx.send(f'Задание {task_id} сделали все ученики')
        return
    if has_role(ctx.message.author, 'pupil'):
        student_id = ctx.message.author.id
    elif has_role(ctx.message.author, 'teacher'):
        student_id = student_string_to_id(ctx, task_id_or_student)
    else:
        return

    tasks_done = set(await database.tasks_done(student_id))
    all_tasks = set(await database.all_task_ids())
    if len(tasks_done) != len(all_tasks):
        tasks_undone = all_tasks.difference(tasks_done)
        await ctx.send(f'Ученик <@{student_id}> не сделал задания: ' + ', '.join([f'<@{i}>' for i in tasks_undone]))
    else:
        await ctx.send(f'Ученик <@{student_id}> сделал все задания')'''