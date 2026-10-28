"""Send one explicit synthetic test. Use one stable ID to avoid repeated tests."""
from bark_server import notify
if __name__ == "__main__":
    print(notify("question", "Тест Bark", "Проверка подключения", "Компьютер",
                 "Тест: если вы видите это уведомление, Bark получает сообщения.",
                 "initial-device-test", icon="question"))
