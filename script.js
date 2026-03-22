const API_URL = "http://localhost:5000/api";

document.addEventListener('DOMContentLoaded', () => {
    const grid = document.getElementById('grid');
    const rows = ['А', 'Б', 'В', 'Г', 'Д'];

    // 1. Создаем ячейки
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

    // 2. Создаем эквалайзер
    const barsContainer = document.querySelector('.bars');
    for (let i = 0; i < 35; i++) {
        const bar = document.createElement('div');
        bar.className = 'bar';
        bar.style.animationDelay = `${Math.random() * 0.5}s`;
        barsContainer.appendChild(bar);
    }

    // 3. Меню
    const sidebar = document.getElementById('sidebar');
    document.getElementById('menu-btn').onclick = () => sidebar.classList.add('open');
    document.getElementById('close-btn').onclick = () => sidebar.classList.remove('open');
    document.getElementById('btn-reset').onclick = () => fetch(`${API_URL}/command?action=off`);

    // 4. Обновление данных
    async function update() {
        try {
            const res = await fetch(`${API_URL}/status`);
            const data = await res.json();

            // Сброс
            document.querySelectorAll('.cell').forEach(el => {
                el.classList.remove('filled', 'error');
                el.querySelector('.cell-content').innerText = 'EMPTY';
                el.querySelector('.cell-content').classList.add('empty-text');
                el.querySelector('.cell-qty').innerText = '';
            });

            // Инвентарь
            for (const [id, items] of Object.entries(data.inventory)) {
                const el = document.getElementById(`cell-${id}`);
                if (el && items.length > 0) {
                    el.classList.add('filled');
                    const content = el.querySelector('.cell-content');
                    content.classList.remove('empty-text');
                    content.innerText = [...new Set(items)].join(', ');
                    el.querySelector('.cell-qty').innerText = `QTY: ${items.length}`;
                }
            }

            // Ошибки (подсветка ячеек)
            data.errors.forEach(e => {
                const match = e.msg.match(/([АБВГД][1-5])/i);
                if (match) {
                    const el = document.getElementById(`cell-${match[1].toUpperCase()}`);
                    if (el) el.classList.add('error');
                }
            });

            // Тексты
            document.getElementById('sys-logs').innerHTML = data.logs.map(l => `<div>[${l.time}] ${l.msg}</div>`).join('');
            document.getElementById('sys-errors').innerHTML = data.errors.map(e => `<div>[${e.time}] ${e.msg}</div>`).join('');
            document.getElementById('esp-status').innerText = `⚙ [ESP-32: ${data.esp_status}]`;

        } catch (e) {
            document.getElementById('esp-status').innerText = `⚙ [BACKEND OFFLINE]`;
        }
    }

    setInterval(update, 1500);
});