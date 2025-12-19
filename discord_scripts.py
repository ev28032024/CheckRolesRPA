"""
JavaScript скрипты для работы с Discord
Вынесены в отдельный модуль для лучшей читаемости и поддержки
"""

# Скрипт для сбора ролей пользователя
ROLES_COLLECTION_SCRIPT = """
(async () => {
    function waitForElement(selector, timeout = 10000, root = document) {
        return new Promise((resolve, reject) => {
            const found = root.querySelector(selector);
            if (found) return resolve(found);
            
            const observer = new MutationObserver(() => {
                const el = root.querySelector(selector);
                if (el) {
                    observer.disconnect();
                    resolve(el);
                }
            });
            
            observer.observe(root === document ? document.documentElement : root, {
                childList: true,
                subtree: true
            });
            
            setTimeout(() => {
                observer.disconnect();
                reject(new Error('Timeout waiting for ' + selector));
            }, timeout);
        });
    }
    
    function sleep(ms) {
        return new Promise(r => setTimeout(r, ms));
    }
    
    // Ищем контейнер со списком участников
    function findMembersScroller() {
        const item = document.querySelector('div[role="listitem"][data-list-item-id^="members-"]');
        if (!item) return null;
        
        let el = item.parentElement;
        while (el) {
            const style = getComputedStyle(el);
            if (
                el.scrollHeight > el.clientHeight + 20 &&
                (style.overflowY === 'auto' ||
                 style.overflowY === 'scroll' ||
                 style.overflowY === 'overlay' ||
                 style.overflowY === 'hidden')
            ) {
                return el;
            }
            el = el.parentElement;
        }
        return null;
    }
    
    // Скроллим и ищем пользователя
    async function scrollToFindUser(displayName, accountName, scroller) {
        const maxSteps = 400;
        const step = Math.max(100, Math.floor(scroller.clientHeight * 0.8));
        scroller.scrollTop = 0;
        await sleep(300);
        
        let prevItemsCount = 0;
        let stuckCounter = 0;
        
        for (let i = 0; i < maxSteps; i++) {
            await sleep(150);
            
            const items = document.querySelectorAll(
                'div[role="listitem"][data-list-item-id^="members-"]'
            );
            
            if (items.length === prevItemsCount) {
                stuckCounter++;
                if (stuckCounter > 3) {
                    await sleep(300);
                    stuckCounter = 0;
                }
            } else {
                stuckCounter = 0;
                prevItemsCount = items.length;
            }
            
            for (const item of items) {
                const nameSpan =
                    item.querySelector('span.name__703b9.username__703b9') ||
                    item.querySelector('span.username__5d473') ||
                    item.querySelector('span[class*="username"]');
                const dn = nameSpan ? nameSpan.textContent.trim() : '';
                if (!dn) continue;
                
                const avatar = item.querySelector('div.wrapper__44b0c[role="img"]');
                const aria = avatar ? (avatar.getAttribute('aria-label') || '') : '';
                
                const displayMatch = dn === displayName;
                const usernameMatch = accountName && aria.startsWith(accountName + ',');
                
                if (displayMatch && (!accountName || usernameMatch)) {
                    return item;
                }
                
                if (displayMatch && !accountName) {
                    return item;
                }
            }
            
            if (scroller.scrollTop + scroller.clientHeight >= scroller.scrollHeight - 5) {
                break;
            }
            
            scroller.scrollTop += step;
        }
        return null;
    }
    
    async function collectRolesAndClose(closeMembersAfter = false) {
        // Ждем появления ролей
        try {
            await waitForElement(
                'div[role="listitem"][data-list-item-id^="roles-"], .role_dfa8b6.pill_dfa8b6, .expandButton_fccfdf',
                10000
            );
        } catch (e) {
            console.log('Роли не найдены или таймаут');
        }
        
        await sleep(250);
        
        // Нажимаем "View All Roles" если есть
        const expandBtn =
            document.querySelector('.expandButton_fccfdf[role="button"]') ||
            document.querySelector('div[class*="expandButton"][role="button"]');
        
        if (expandBtn) {
            expandBtn.dispatchEvent(
                new MouseEvent('click', { bubbles: true, cancelable: true, view: window })
            );
            await sleep(200);
        }
        
        // Собираем роли
        const roleEls = document.querySelectorAll(
            'div[role="listitem"][data-list-item-id^="roles-"], .role_dfa8b6.pill_dfa8b6'
        );
        
        const roles = [];
        roleEls.forEach(el => {
            let name = el.getAttribute('aria-label');
            if (!name) {
                const nameNode =
                    el.querySelector('.overflow_b0dfc2') ||
                    el.querySelector('.roleName_dfa8b6') ||
                    el.querySelector('.defaultColor__4bd52') ||
                    el;
                name = (nameNode.textContent || '').trim();
            }
            if (!name) return;
            if (name.length > 50) return;
            roles.push(name);
        });
        
        const uniqueRoles = [...new Set(roles)];
        const rolesText = uniqueRoles.join('|');
        
        // Закрываем попап
        document.dispatchEvent(new KeyboardEvent('keydown', {
            key: 'Escape',
            code: 'Escape',
            keyCode: 27,
            bubbles: true
        }));
        
        await sleep(200);
        
        if (closeMembersAfter) {
            const toggleClose =
                document.querySelector('.iconWrapper__9293f[role="button"][aria-label*="Member List"]') ||
                document.querySelector('[role="button"][aria-label*="Member List"]') ||
                document.querySelector('[role="button"][aria-label*="Список участников"]');
            if (toggleClose) {
                toggleClose.dispatchEvent(
                    new MouseEvent('click', { bubbles: true, cancelable: true, view: window })
                );
                await sleep(100);
            }
        }
        
        return rolesText;
    }
    
    try {
        // Получаем displayName и username из nameTag
        const nameTagRoot =
            document.querySelector('.nameTag__37e49') ||
            document.querySelector('div[class*="nameTag"]');
        
        if (!nameTagRoot) {
            console.error('Не найден nameTag');
            return '';
        }
        
        const displayNameNode = nameTagRoot.querySelector('[data-text-variant="text-md/medium"]');
        const displayName = displayNameNode ? displayNameNode.textContent.trim() : null;
        
        const usernameNode =
            nameTagRoot.querySelector('.hovered__0263c') ||
            nameTagRoot.querySelector('.panelSubtextContainer__37e49');
        const accountName = usernameNode ? usernameNode.textContent.trim() : null;
        
        if (!displayName) {
            console.error('Не удалось получить displayName');
            return '';
        }
        
        // Открываем список участников
        let openedMembersPanel = false;
        let anyMember = document.querySelector(
            'div[role="listitem"][data-list-item-id^="members-"]'
        );
        
        if (!anyMember) {
            const toggle =
                document.querySelector('.iconWrapper__9293f[role="button"][aria-label*="Member List"]') ||
                document.querySelector('[role="button"][aria-label*="Member List"]') ||
                document.querySelector('[role="button"][aria-label*="Список участников"]');
            
            if (toggle) {
                toggle.dispatchEvent(
                    new MouseEvent('click', { bubbles: true, cancelable: true, view: window })
                );
                openedMembersPanel = true;
            }
            
            try {
                anyMember = await waitForElement(
                    'div[role="listitem"][data-list-item-id^="members-"]',
                    10000
                );
            } catch (e) {
                console.error('Не удалось открыть список участников');
                return '';
            }
        }
        
        await sleep(300);
        
        const scroller = findMembersScroller();
        if (!scroller) {
            console.error('Не найден скроллер участников');
            return '';
        }
        
        const userItem = await scrollToFindUser(displayName, accountName, scroller);
        if (!userItem) {
            console.error('Не найден пользователь в списке участников');
            return '';
        }
        
        userItem.dispatchEvent(
            new MouseEvent('click', { bubbles: true, cancelable: true, view: window })
        );
        
        // Собираем роли
        const rolesText = await collectRolesAndClose(openedMembersPanel);
        return rolesText;
        
    } catch (e) {
        console.error('Ошибка в скрипте:', e);
        return '';
    }
})()
"""

# Скрипт для проверки авторизации
AUTH_CHECK_SCRIPT = """
() => {
    try {
        // Проверка 1: путь не начинается с /login
        const isAuthedByPath = !location.pathname.startsWith('/login');
        
        // Проверка 2: наличие элемента с ссылкой на DM
        const hasDM = !!document.querySelector('a[href="/channels/@me"]');
        
        // Проверка 3: наличие других признаков авторизации
        const hasSidebar = !!document.querySelector('[class*="sidebar"]');
        const hasGuild = !!document.querySelector('[class*="guild"]');
        
        return isAuthedByPath || hasDM || (hasSidebar && hasGuild);
    } catch(e) {
        return false;
    }
}
"""

# Скрипт для проверки доступа к каналу
CHANNEL_ACCESS_SCRIPT = """
() => {
    try {
        // Шаг 1: Ждём DOM-ready
        if (document.readyState !== 'complete') {
            return null;
        }
        
        // Шаг 2: Поиск текстового div
        const textDiv = document.querySelector('div[class*="defaultColor__"][data-text-variant="text-sm/medium"]') ||
                      document.querySelector('div[class*="defaultColor__"]');
        
        if (!textDiv) {
            return null;
        }
        
        // Шаг 3: Извлечение текста
        const text = textDiv.textContent.trim();
        if (!text) {
            return null;
        }
        
        return text;
    } catch (e) {
        return null;
    }
}
"""

