from webdav3.client import Client

class DirectoryException(Exception):
    pass


class MailWevDAV:
    def __init__(self, login: str, password: str):
        """
        Инициализация клиента WebDAV
        """
        self.options = {
            'webdav_hostname': "https://webdav.cloud.mail.ru/",
            'webdav_login': login,
            'webdav_password': password
        }
        self.client = Client(self.options)

    async def test_connection(self):
        """Проверка соединения с облаком"""
        try:
            files = self.client.list()
            print(f'Подключение успешно!\nДоступные файлы:\n{files}')
            return True
        except Exception as e:
            print(f'Ошибка подключения: {e}')
            return False
        
    async def upload_file(self, local_path: str, remote_path: str):
        """Загрузка файлов в облако"""
        try:
            self.client.upload_async(remote_path=remote_path, local_path=local_path)
            print(f'файл {local_path} был загружен в {remote_path}')
            return True
        except Exception as e:
            print(f'Файл {local_path}, ошибка при загрузке\n\n{e}')
            return False
    
    async def check_dir(self, path):
        try:
            if self.client.check(path):
                print('Такая директория есть')
                return True
            else:
                print('Такой директории нет')
                return False
        except Exception as e:
            print(f'Ошибка при проверке директории: {e}')

    async def create_dir(self, path):
        try:
            self.client.mkdir(path)
            print('Директория создается')
        except (Exception, DirectoryException) as e:
            print(e)