const API_URL = "http://localhost:5000/api";

document.addEventListener('DOMContentLoaded', () => {
    const grid = document.getElementById('grid');
    const rows = ['А', 'Б', 'В', 'Г', 'Д'];
    // ТЕПЕРЬ 10 КОЛОНОК
    const cols = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]; 
    let lastEventTime = 0;

    function toRussianLetter(str) {
        const engToRus = {'A':'А', 'B':'Б', 'V':'В', 'G':'Г', 'D':'Д'};
        let firstChar = str.charAt(0).toUpperCase();
        return (engToRus[firstChar] || firstChar) + str.slice(1);
    }

    rows.forEach(r => {
        cols.forEach(c => {
            const id = `${r}${c}`;
            const div = document.createElement('div');
            div.className = 'cell';
            div.id = `cell-${id}`;
            div.innerHTML = `<div class="cell-id">${id}</div><div class="cell-content empty-text">EMPTY</div><div class="cell-qty"></div>`;
            grid.appendChild(div);
        });
    });

    const barsContainer = document.querySelector('.bars');
    if (barsContainer) {
        for (let i = 0; i < 35; i++) {
            const bar = document.createElement('div');
            bar.className = 'bar';
            bar.style.animationDelay = `${Math.random() * 0.5}s`;
            barsContainer.appendChild(bar);
        }
    }

    const sidebar = document.getElementById('sidebar');
    const menuBtn = document.getElementById('menu-btn');
    const closeBtn = document.getElementById('close-btn');
    const resetBtn = document.getElementById('btn-reset');

    if (menuBtn && sidebar) menuBtn.onclick = () => sidebar.classList.add('open');
    if (closeBtn && sidebar) closeBtn.onclick = () => sidebar.classList.remove('open');
    if (resetBtn) resetBtn.onclick = () => fetch(`${API_URL}/command?action=off`);

    async function update() {
        try {
            const res = await fetch(`${API_URL}/status`);
            if (!res.ok) throw new Error(`HTTP error!`);
            const data = await res.json();

            const statusEl = document.getElementById('esp-status');
            if (statusEl) statusEl.innerText = `⚙ [ESP-32: ${data.esp_status || 'UNKNOWN'}]`;

            document.querySelectorAll('.cell').forEach(el => {
                el.classList.remove('filled', 'error');
                const content = el.querySelector('.cell-content');
                const qty = el.querySelector('.cell-qty');
                if (content) { content.innerText = 'EMPTY'; content.classList.add('empty-text'); }
                if (qty) qty.innerText = '';
            });

            if (data.inventory) {
                for (const [rawId, items] of Object.entries(data.inventory)) {
                    const cellId = toRussianLetter(rawId); 
                    const el = document.getElementById(`cell-${cellId}`);
                    if (el && Array.isArray(items) && items.length > 0) {
                        el.classList.add('filled');
                        const content = el.querySelector('.cell-content');
                        const qty = el.querySelector('.cell-qty');
                        if (content) {
                            content.classList.remove('empty-text');
                            content.innerText = [...new Set(items)].join(', ');
                        }
                        if (qty) qty.innerText = `QTY: ${items.length}`;
                    }
                }
            }

            if (data.last_action && data.last_action.time > lastEventTime) {
                const actionCellId = toRussianLetter(data.last_action.cell);
                const cellEl = document.getElementById(`cell-${actionCellId}`);
                if (cellEl) {
                    cellEl.classList.add('pulse-flash');
                    setTimeout(() => cellEl.classList.remove('pulse-flash'), 1000);
                }
                lastEventTime = data.last_action.time;
            }

            if (data.errors && Array.isArray(data.errors)) {
                data.errors.forEach(e => {
                    // РЕГУЛЯРКА ИЩЕТ ДО 10
                    const match = e.msg.match(/([АБВГДA-D](?:10|[1-9]))/i);
                    if (match) {
                        const cellId = toRussianLetter(match[1]);
                        const el = document.getElementById(`cell-${cellId}`);
                        if (el) el.classList.add('error');
                    }
                });
            }

            const sysLogs = document.getElementById('sys-logs');
            const sysErrors = document.getElementById('sys-errors');
            if (sysLogs && data.logs) sysLogs.innerHTML = data.logs.map(l => `<div>[${l.time}] ${l.msg}</div>`).join('');
            if (sysErrors && data.errors) sysErrors.innerHTML = data.errors.map(e => `<div>[${e.time}] ${e.msg}</div>`).join('');

        } catch (e) {
            const statusEl = document.getElementById('esp-status');
            if (statusEl) statusEl.innerText = `⚙ [BACKEND OFFLINE]`;
        }
    }
    setInterval(update, 1500);
    update();
});