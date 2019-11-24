import asyncpg
import os


async def init():
    global conn
    conn = await asyncpg.connect(os.environ.get('DATABASE_URL', None), ssl='require')
    await conn.execute('''CREATE TABLE IF NOT EXISTS tasks (
                      id int PRIMARY KEY,
                      file bytea NOT NULL,
                      file_name text,
                      description text )''')

    await conn.execute('''CREATE TABLE IF NOT EXISTS solutions (
                      student_id bigint NOT NULL,
                      task_id int NOT NULL,
                      file bytea NOT NULL,
                      file_name text )''')

    await conn.execute('''CREATE TABLE IF NOT EXISTS marks (
                      mark int NOT NULL,
                      task_id int NOT NULL,
                      student_id bigint NOT NULL )''')


async def add_task(file, file_name, description):
    global conn
    ids = [i.id for i in await conn.fetch('''SELECT id FROM tasks''')]
    if ids:
        new_id = max([i[0] for i in ids]) + 1
    else:
        new_id = 1
    await conn.execute('INSERT INTO tasks VALUES ($1, $2, $3, $4)', new_id, file, file_name, description)
    return new_id


async def get_task(task_id, description_only=False):
    global conn
    if description_only:
        result = await conn.fetchrow('SELECT description FROM tasks WHERE id = $1', task_id)
        return result.description
    else:
        result = await conn.fetchrow('SELECT file, file_name, description FROM tasks WHERE id = $1', task_id)
        if result:
            return tuple(result)
        return None


async def add_solution(student_id, task_id, file, file_name):
    global conn
    await conn.execute('REPLACE INTO solutions VALUES ($1, $2, $3, $4)', student_id, task_id, file, file_name)


async def get_solution(task_id, student_id):
    global conn
    result = await conn.fetchrow('SELECT file, file_name FROM solutions WHERE student_id = $1 AND task_id = $2',
                                     student_id, task_id)
    if result:
        return tuple(result)
    return None


async def who_has_solution(task_id):
    global conn
    result = await conn.fetch('SELECT student_id FROM solutions WHERE task_id = $1', task_id)
    if result:
        return [i.student_id for i in result]
    return None


async def tasks_done(student_id):
    global conn
    result = await conn.fetch('SELECT task_id FROM solutions WHERE student_id = $1', student_id)
    if result:
        return [i.task_id for i in result]
    return None


async def all_task_ids():
    global conn
    result = await conn.fetch('SELECT id FROM tasks')
    if result:
        return [i.id for i in result]
    return None


async def add_mark(mark, task_id, student_id):
    global conn
    await conn.execute('REPLACE INTO marks VALUES ($1, $2, $3)', mark, task_id, student_id)


async def get_mark(task_id, student_id):
    global conn
    return await conn.fetchval('SELECT mark FROM marks WHERE task_id = $1 AND student_id = $2', task_id, student_id)


async def get_marks(student_id):
    result = await conn.fetch('SELECT mark FROM marks WHERE student_id = $1', student_id)
    if result:
        return [i.mark for i in result]
    return None


async def close():
    global conn
    await conn.close()
