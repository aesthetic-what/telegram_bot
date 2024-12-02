import sqlite3


class DataBase:
    def __init__(self, name_db):
        self.connect = sqlite3.connect(name_db)
        self.cursor = self.connect.cursor()

    async def get_projects(self, chat_id):
        with self.connect:
            return self.cursor.execute(
                """SELECT project_name FROM projects WHERE manager_id LIKE ?""",
                (chat_id,),
            ).fetchall()

    async def take_client_id(self, project_name):
        """
        Это sql запрос с помощью которого я найду пользователя которому нужно отправить файлы
        """
        with self.connect:
            return self.cursor.execute(
                """SELECT u.chat_id
                    FROM users u 
                    JOIN projects p ON u.chat_id = p.client_id 
                    WHERE project_name = (?)""",
                (project_name,),
            ).fetchone()

    async def take_client_name(self, chat_id):
        with self.connect:
            return self.cursor.execute(
                """SELECT name FROM users WHERE chat_id=(?)""", (chat_id,)
            ).fetchone()

    async def add_link(self, link, project_name):
        with self.connect:
            return self.cursor.execute(
                """UPDATE projects SET group_chat=(?) WHERE project_name=(?)""",
                (link, project_name, ),
            )

    async def update_status(self, status, project_name):
        """Это функция для обновления статуса проекта"""
        with self.connect:
            return self.cursor.execute(
                """UPDATE projects SET status=(?) WHERE project_name=(?)""",
                (status, project_name),
            )

    async def remember(self):
        with self.connect:
            return self.cursor.execute(
                """SELECT project_name, client_id FROM projects WHERE status='waiting'"""
            ).fetchall()

    async def complete_project(self, project_name):
        with self.connect:
            return self.cursor.execute(
                """UPDATE projects SET status='complete' WHERE project_name=(?)""",
                (project_name,),
            )

    async def add_token(self, project_name, token):
        """Paste token in current project"""
        with self.connect:
            return self.cursor.execute(
                """UPDATE projects SET token=(?) WHERE project_name=(?)""",
                (
                    token,
                    project_name,
                ),
            )

    async def confirm_user(self, token, chat_id, name):
        """Verify current token in database and attack client into project"""
        with self.connect:
            result = self.cursor.execute(
                """SELECT 1 FROM projects WHERE token=(?)""", (token,)
            ).fetchone()

            if result:
                self.cursor.execute(
                    """INSERT INTO users(chat_id, name) VALUES(?, ?)""", (chat_id, name)
                )
                return True
            else:
                return False

    async def add_to_project(self, chat_id, token):
        with self.connect:
            project_name = self.cursor.execute(
                """SELECT project_name FROM projects WHERE token=(?)""", (token,)
            ).fetchone()
            return self.cursor.execute(
                """UPDATE projects SET client_id=(SELECT chat_id FROM users WHERE chat_id=(?)) WHERE project_name=(?)""",
                (chat_id, project_name[0]),
            )

    async def take_project_name(self, token):
        with self.connect:
            return self.cursor.execute(
                """SELECT project_name FROM projects WHERE token=(?)""", (token,)
            ).fetchone()
