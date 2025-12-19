# CheckRolesRPA - Чекер ролей Discord

Универсальный софт-чекер ролей для Discord с точечной настройкой через Google таблицы и интеграцией с ADSpower API.

## Структура Google таблицы

### Лист `ds_data` (название настраивается в config.py)
Страница для данных профиля через которого будет проходить отработка.

**Столбцы (первая строка - заголовки):**
- `serial_number` - серийный номер профиля ADSpower
- `email` - email для авторизации в Discord
- `password` - пароль для авторизации в Discord
- `username` - ожидаемый username в Discord (опционально, для проверки)

**Пример:**
| serial_number | email | password | username |
|---------------|-------|----------|----------|
| 1234567890 | user@example.com | password123 | username#1234 |

**Примечание:** Название листа по умолчанию `ds_data`, но можно изменить в `config.yaml` или через переменную окружения `GOOGLE_SHEET_DS_DATA`.

### Лист `ds_link` (название настраивается в config.yaml)
Страница для указания ссылок на Discord каналы/серверы.

**Столбцы (первая строка - заголовки):**
- `link` - ссылка на Discord сервер (например: `https://discord.com/channels/XXXXXXX`)

**Пример:**
| link |
|------|
| https://discord.com/channels/123456789012345678 |
| https://discord.com/channels/987654321098765432 |

**Примечание:** Название листа по умолчанию `ds_link`, но можно изменить в `config.yaml` или через переменную окружения `GOOGLE_SHEET_DS_LINK`.

### Лист `чек-отработка` (название настраивается в config.yaml)
Страница для заполнения профилями для чекера и записи результатов.

**Столбцы (результаты, добавляются автоматически):**
- `username` - проверенный username
- `serial_number` - серийный номер профиля
- `found` - найден ли пользователь (True/False)
- `roles` - список ролей через запятую
- `timestamp` - время проверки (формат: YYYY-MM-DD HH:MM:SS)
- `error` - ошибка (если была)

**Пример входных данных:**
| username | serial_number |
|----------|---------------|
| user1#1234 | |
| user2#5678 | |
| @user3 | |

**Пример результатов (добавляются автоматически):**
| username | serial_number | found | roles | timestamp | error |
|----------|---------------|-------|-------|-----------|-------|
| user1#1234 | | True | Admin, Moderator | 2024-01-15 10:30:00 | |
| user2#5678 | | False | Нет ролей | 2024-01-15 10:30:05 | |

**Примечание:** Название листа по умолчанию `чек-отработка`, но можно изменить в `config.yaml` или через переменную окружения `GOOGLE_SHEET_CHECK`.

## Установка

1. Клонируйте репозиторий или скачайте файлы

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

**Примечание:** Проект использует [patchright](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright) - undetected версию Playwright для обхода детекции автоматизации.

3. Настройте Google Sheets API:
   - Создайте проект в [Google Cloud Console](https://console.cloud.google.com/)
   - Включите Google Sheets API
   - Создайте Service Account
   - Скачайте JSON файл с credentials
   - Сохраните его как `credentials.json` в корне проекта
   - Поделитесь Google таблицей с email из Service Account

4. Настройте конфигурацию:
   
   **Вариант 1: YAML файл (рекомендуется)**
   ```bash
   # Скопируйте пример конфигурации
   cp config.example.yaml config.yaml
   # Отредактируйте config.yaml и укажите свои настройки
   ```
   
   **Вариант 2: Переменные окружения**
   ```bash
   # Windows PowerShell
   $env:GOOGLE_SHEETS_ID="your_spreadsheet_id"
   $env:ADSPOWER_API_URL="http://local.adspower.net:50325"
   $env:ADSPOWER_API_KEY="your_api_key"  # Опционально, для локального API обычно не требуется
   $env:LOG_LEVEL="INFO"
   
   # Настройка названий листов Google Sheets (опционально)
   $env:GOOGLE_SHEET_DS_DATA="ds_data"
   $env:GOOGLE_SHEET_DS_LINK="ds_link"
   $env:GOOGLE_SHEET_CHECK="чек-отработка"
   ```

## Логирование

Логи сохраняются в файл `checker.log` и выводятся в консоль.

Уровни логирования:
- `DEBUG` - детальная информация
- `INFO` - общая информация
- `WARNING` - предупреждения
- `ERROR` - ошибки

