"""
Селекторы для работы с Discord
Централизованное хранение селекторов для упрощения поддержки
"""

# Селекторы для проверки авторизации
AUTH_SELECTORS = [
    "a[href='/channels/@me']",
    "[class*='sidebar']",
    "[class*='guild']",
    "[data-list-id]"
]

# Селекторы для формы логина
LOGIN_FORM_SELECTORS = [
    "input[name='email']",
    "input[type='email']"
]

# Селекторы для полей ввода
EMAIL_INPUT_SELECTORS = [
    "input[name='email']",
    "input[type='email']"
]

PASSWORD_INPUT_SELECTORS = [
    "input[name='password']",
    "input[type='password']"
]

LOGIN_BUTTON_SELECTORS = [
    "button[type='submit']"
]

# Селекторы для поиска пользователей
SEARCH_INPUT_SELECTORS = [
    "input[placeholder*='Search']",
    "input[placeholder*='поиск']",
    "input[type='text'][aria-label*='Search']",
    "div[class*='search'] input"
]

SEARCH_RESULT_SELECTORS = [
    "[class*='result']",
    "[class*='member']",
    "[class*='user']",
    "[class*='searchResult']",
    "div[class*='user']"
]

# Селекторы для username
USERNAME_SELECTORS = [
    "[class*='username']",
    "[class*='nameTag']",
    "[data-user-id]",
    "div[class*='user'] span",
    "[class*='nameTagText']"
]

# Селекторы для ролей
ROLE_SELECTORS = [
    "div[role='listitem'][data-list-item-id^='roles-']",
    ".role_dfa8b6.pill_dfa8b6",
    "[class*='role']",
    "[class*='badge']",
    "span[class*='role']",
    "div[class*='role']",
    "[data-role-id]"
]

# Селекторы для элементов авторизации
AUTHORIZED_ELEMENTS = [
    "[class*='sidebar']",
    "[class*='guild']",
    "[data-list-id]",
    "[class*='scroller']",
    "div[class*='base']"
]

