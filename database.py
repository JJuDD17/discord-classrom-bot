import aiosqlite


async def init(db_file):
    global db
    db = await aiosqlite.connect(db_file)
    await db.execute('''CREATE TABLE IF NOT EXISTS tasks (
                      id int PRIMARY KEY,
                      file mediumblob NOT NULL,
                      file_name text,
                      description text )''')

    await db.execute('''CREATE TABLE IF NOT EXISTS solutions (
                      student_id bigint NOT NULL,
                      task_id int NOT NULL,
                      file mediumblob NOT NULL,
                      file_name text )''')

    await db.execute('''CREATE TABLE IF NOT EXISTS marks (
                      mark int NOT NULL,
                      task_id int NOT NULL,
                      student_id bigint NOT NULL )''')

    await db.commit()


async def add_task(file, file_name, description):
    global db
    ids = await (await db.execute('''SELECT id FROM tasks''')).fetchall()
    if ids:
        new_id = max([i[0] for i in ids]) + 1
    else:
        new_id = 1
    await db.execute('INSERT INTO tasks VALUES (?, ?, ?, ?)', (new_id, file, file_name, description))
    await db.commit()
    return new_id


async def get_task(task_id, description_only=False):
    global db
    if description_only:
        result = await (await db.execute('SELECT description FROM tasks WHERE id = ?', (task_id,))).fetchone()
        if result:
            return result[0]
        else:
            return None
    else:
        return await (await db.execute(
            'SELECT file, file_name, description FROM tasks WHERE id = ?', (task_id,))).fetchone()


async def add_solution(student_id, task_id, file, file_name):
    global db
    await db.execute('REPLACE INTO solutions VALUES (?, ?, ?, ?)', (student_id, task_id, file, file_name))
    await db.commit()


async def get_solution(task_id, student_id):
    global db
    return await (await db.execute('SELECT file, file_name FROM solutions WHERE student_id = ? AND task_id = ?',
                                   (student_id, task_id))).fetchone()


async def who_has_solution(task_id):
    global db
    return [i[0] for i in
            await (await db.execute('SELECT student_id FROM solutions WHERE task_id = ?',
                                    (task_id,))).fetchall()]


async def tasks_done(student_id):
    global db
    return [i[0] for i in
            await (await db.execute('SELECT task_id FROM solutions WHERE student_id = ?',
                                    (student_id,))).fetchall()]


async def all_task_ids():
    global db
    return [i[0] for i in await (await db.execute('SELECT id FROM tasks')).fetchall()]


async def add_mark(mark, task_id, student_id):
    global db
    await db.execute('REPLACE INTO marks VALUES (?, ?, ?)', (mark, task_id, student_id))
    await db.commit()


async def get_mark(task_id, student_id):
    global db
    result = await (await db.execute('SELECT mark FROM marks WHERE task_id = ? AND student_id = ?',
                                     (task_id, student_id))).fetchone()
    if result:
        return result[0]
    return None


async def get_marks(student_id):
    return [i[0] for i in
            await (await db.execute('SELECT mark FROM marks WHERE student_id = ?', (student_id,))).fetchall()]


async def close():
    global db
    await db.close()
