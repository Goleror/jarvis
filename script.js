const API_URL = "http://localhost:5000/api";

document.addEventListener('DOMContentLoaded', () => {
    const grid = document.getElementById('grid');
    const rows = ['А', 'Б', 'В', 'Г', 'Д'];

    // 1. Создаем ячейки (ID - А1, Б2 и т.д.)
    rows.forEach(r => {
        for (let c = 1; c <= 5; c++) {
            const id = `${r}${c}`;
            const div = document.createElement('div');
            div.className = 'cell';
            div.id = `cell-${id}`;
            div.innerHTML = `<div class="cell-id">${id}</div><div class="cell-content empty-text">EMPTY</div><div class="cell-qty"></div>`;
            grid.appendChild(div);
        }
    });

    // 2. Создаем визуализатор (эквалайзер)
    const barsContainer = document.querySelector('.bars');
    if (barsContainer) {
        for (let i = 0; i < 35; i++) {
            const bar = document.createElement('div');
            bar.className = 'bar';
            bar.style.animationDelay = `${Math.random() * 0.5}s`;
            barsContainer.appendChild(bar);
        }
    }

    // 3. Управление меню
    const sidebar = document.getElementById('sidebar');
    const menuBtn = document.getElementById('menu-btn');
    const closeBtn = document.getElementById('close-btn');
    const resetBtn = document.getElementById('btn-reset');

    if (menuBtn && sidebar) menuBtn.onclick = () => sidebar.classList.add('open');
    if (closeBtn && sidebar) closeBtn.onclick = () => sidebar.classList.remove('open');
    if (resetBtn) resetBtn.onclick = () => fetch(`${API_URL}/command?action=off`);

    // Вспомогательная функция для перевода A (англ) в А (рус)
    // чтобы не было конфликтов при поиске элемента по ID
    function toRussianLetter(str) {
        const engToRus = {'A':'А', 'B':'Б', 'V':'В', 'G':'Г', 'D':'Д'};
        let firstChar = str.charAt(0).toUpperCase();
        return (engToRus[firstChar] || firstChar) + str.slice(1);
    }

    // 4. Основная функция обновления
    async function update() {
        try {
            const res = await fetch(`${API_URL}/status`);
            
            // Проверка, что ответ действительно пришел (200 OK)
            if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
            
            const data = await res.json();

            // Если данные пришли успешно, меняем статус на CONNECTED
            const statusEl = document.getElementById('esp-status');
            if (statusEl) {
                statusEl.innerText = `⚙ [ESP-32: ${data.esp_status || 'UNKNOWN'}]`;
                statusEl.classList.remove('error-text'); // Можно добавить стиль для ошибки потом
            }

            // 4.1. Сброс визуального состояния всех ячеек
            document.querySelectorAll('.cell').forEach(el => {
                el.classList.remove('filled', 'error');
                const content = el.querySelector('.cell-content');
                const qty = el.querySelector('.cell-qty');
                if (content) {
                    content.innerText = 'EMPTY';
                    content.classList.add('empty-text');
                }
                if (qty) qty.innerText = '';
            });

            // 4.2. Обновление инвентаря
            if (data.inventory) {
                for (const [rawId, items] of Object.entries(data.inventory)) {
                    // Принудительно делаем букву русской для поиска по ID HTML
                    const cellId = toRussianLetter(rawId); 
                    const el = document.getElementById(`cell-${cellId}`);
                    
                    // Проверяем, что ячейка найдена в HTML и в ней есть предметы
                    if (el && Array.isArray(items) && items.length > 0) {
                        el.classList.add('filled');
                        const content = el.querySelector('.cell-content');
                        const qty = el.querySelector('.cell-qty');
                        
                        if (content) {
                            content.classList.remove('empty-text');
                            // Берем только уникальные названия, чтобы не писать "болт, болт"
                            const uniqueItems = [...new Set(items)];
                            content.innerText = uniqueItems.join(', ');
                        }
                        if (qty) {
                            qty.innerText = `QTY: ${items.length}`;
                        }
                    }
                }
            }

            // 4.3. Подсветка ячеек с ошибками
            if (data.errors && Array.isArray(data.errors)) {
                data.errors.forEach(e => {
                    const match = e.msg.match(/([АБВГДA-D][1-5])/i);
                    if (match) {
                        const cellId = toRussianLetter(match[1]);
                        const el = document.getElementById(`cell-${cellId}`);
                        if (el) el.classList.add('error');
                    }
                });
            }

            // 4.4. Обновление списков логов и ошибок
            const sysLogs = document.getElementById('sys-logs');
            const sysErrors = document.getElementById('sys-errors');
            
            if (sysLogs && data.logs) {
                sysLogs.innerHTML = data.logs.map(l => `<div>[${l.time}] ${l.msg}</div>`).join('');
            }
            if (sysErrors && data.errors) {
                sysErrors.innerHTML = data.errors.map(e => `<div>[${e.time}] ${e.msg}</div>`).join('');
            }

        } catch (e) {
            console.error("Ошибка при обновлении данных:", e);
            const statusEl = document.getElementById('esp-status');
            if (statusEl) {
                statusEl.innerText = `⚙ [BACKEND OFFLINE]`;
            }
        }
    }

    // Запускаем обновление каждые 1.5 секунды
    setInterval(update, 1500);
    // Первый вызов сразу после загрузки
    update();
});