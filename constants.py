"""
Константы для проекта
"""
# Таймауты (в секундах)
DEFAULT_PAGE_LOAD_TIMEOUT = 10
AUTH_CHECK_TIMEOUT = 10
CHANNEL_CHECK_TIMEOUT = 5
ELEMENT_WAIT_TIMEOUT = 3

# Задержки для антидетекта (в секундах)
MIN_DELAY_BEFORE_ACTION = 0.3
MAX_DELAY_BEFORE_ACTION = 0.7
MIN_DELAY_AFTER_ACTION = 0.5
MAX_DELAY_AFTER_ACTION = 1.0
MIN_DELAY_BEFORE_NAVIGATION = 0.5
MAX_DELAY_BEFORE_NAVIGATION = 1.5
MIN_DELAY_AFTER_NAVIGATION = 0.5
MAX_DELAY_AFTER_NAVIGATION = 1.0
MIN_DELAY_BETWEEN_CHECKS = 3
MAX_DELAY_BETWEEN_CHECKS = 4.5

# Вероятности для антидетекта
PAUSE_DURING_TYPING_PROBABILITY = 0.05  # 5%
RANDOM_ACTIVITY_PROBABILITY = 0.3  # 30%

# Discord URLs
DISCORD_LOGIN_URL = "https://discord.com/login"
DISCORD_BASE_URL = "https://discord.com"

# Разделители
ROLES_SEPARATOR = '|'
ROLES_DISPLAY_SEPARATOR = ', '

# Сообщения
NO_ROLES_MESSAGE = 'Нет ролей'
EMPTY_USERNAME_MESSAGE = 'Username не указан'

# Максимальная длина названия роли
MAX_ROLE_NAME_LENGTH = 50

