import os, sys, json, re, time, random, threading, queue, requests
import pymorphy3, winsound, sounddevice as sd, speech_recognition as sr
from flask import Flask, jsonify, request
from flask_cors import CORS
from vosk import Model, KaldiRecognizer

# --- НАСТРОЙКИ ---
ESP_IP = "192.168.9.215"
MODEL_PATH = "model"
INVENTORY_FILE = "inventory.json"
SOUNDS_DIR = "sounds"
AUTO_OFF_TIME = 10.0  # Свет гаснет через 10 сек
SESSION_TIME = 15.0   # Джарвис слушает 15 сек после последней команды

# --- ИНИЦИАЛИЗАЦИЯ ---
morph = pymorphy3.MorphAnalyzer()
app = Flask(__name__)
CORS(app)

logs, errors, inventory = [], [], {}
esp_connected = "OFFLINE"
q = queue.Queue()
led_timer = None 

# --- ФУНКЦИИ ПОДДЕРЖКИ ---

def add_log(msg, is_error=False):
    t = time.strftime("%H:%M:%S")
    entry = {"time": t, "msg": msg}
    if is_error:
        errors.append(entry)
        play_sound("error")
        print(f"!!! [ERR] {msg}")
    else:
        logs.append(entry)
        print(f">>> [LOG] {msg}")

def play_sound(folder):
    path = os.path.join(SOUNDS_DIR, folder)
    if os.path.exists(path):
        files = [f for f in os.listdir(path) if f.endswith(".wav")]
        if files:
            try:
                f = os.path.join(path, random.choice(files))
                winsound.PlaySound(f, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except: pass

def load_inventory():
    global inventory
    if os.path.exists(INVENTORY_FILE):
        try:
            with open(INVENTORY_FILE, 'r', encoding='utf-8') as f: inventory = json.load(f)
        except: inventory = {}
    else: inventory = {}

def save_inventory():
    with open(INVENTORY_FILE, 'w', encoding='utf-8') as f: json.dump(inventory, f, ensure_ascii=False, indent=4)

load_inventory()

def auto_off_action():
    if command_esp("/off"): add_log("System: Автоматическое отключение индикации")

def start_led_timer():
    global led_timer
    if led_timer: led_timer.cancel()
    led_timer = threading.Timer(AUTO_OFF_TIME, auto_off_action)
    led_timer.start()

def command_esp(path):
    global esp_connected
    try:
        requests.get(f"http://{ESP_IP}{path}", timeout=1.5)
        esp_connected = "CONNECTED"
        return True
    except:
        esp_connected = "OFFLINE"
        return False

def extract_cell(text):
    text = text.lower()
    mapping = {'a':'А', 'а':'А', 'b':'Б', 'б':'Б', 'v':'В', 'в':'В', 'w':'В', 'c':'В', 'с':'В', 'g':'Г', 'г':'Г', 'd':'Д', 'д':'Д'}
    match = re.search(r'([а-дa-eвvbcg])\s*([1-5])', text)
    if match:
        l = mapping.get(match.group(1), match.group(1).upper())
        return f"{l}{match.group(2)}"
    return None

# --- ГЛАВНАЯ ЛОГИКА ---
def process_intent(text):
    global led_timer
    text = text.lower()
    cell = extract_cell(text)
    
    # 1. ВЫКЛЮЧИТЬ
    if any(w in text for w in ["выключи", "погаси", "отключи", "пока"]):
        if led_timer: led_timer.cancel()
        command_esp("/off"); add_log("STANDBY Mode Active")
        play_sound("success"); return True # Возвращает True, чтобы закрыть 15-сек сессию

    # 2. ОЧИСТКА ЯЧЕЙКИ
    if "очист" in text or "удали все" in text:
        if cell:
            inventory[cell] = []
            save_inventory()
            command_esp(f"/light?cell={cell}&r=255&g=0&b=0")
            add_log(f"System: Сектор {cell} очищен")
            play_sound("success"); start_led_timer(); return False

    # 3. ПОИСК
    if any(w in text for w in ["где", "найди"]):
        found_cell = None
        search_query = " ".join([morph.parse(w)[0].normal_form for w in text.split() if w not in ["где", "найди", "джарвис"]])
        for c, items in inventory.items():
            for item in items:
                if search_query in item or item in search_query:
                    found_cell = c; break
        if found_cell:
            command_esp(f"/light?cell={found_cell}&r=0&g=255&b=0")
            add_log(f"Locator: сектор {found_cell}")
            play_sound("success"); start_led_timer(); return False
        else:
            add_log(f"Объект не найден", True); return False

    # 4. УДАЛИТЬ ПРЕДМЕТ
    if "удали" in text or "убери" in text:
        if cell:
            words = [morph.parse(w)[0].normal_form for w in text.split()]
            for item in inventory.get(cell, []):
                if morph.parse(item)[0].normal_form in words:
                    inventory[cell].remove(item); save_inventory()
                    command_esp(f"/light?cell={cell}&r=255&g=0&b=0")
                    add_log(f"Modified: {item} удален")
                    play_sound("success"); start_led_timer(); return False

    # 5. ДОБАВЛЕНИЕ / ПОДСВЕТКА
    if cell:
        forbidden = ["джарвис", "ячейка", "личинка", "добавь", "запиши", "в", "на", cell.lower()]
        clean_words = [morph.parse(w)[0].normal_form for w in text.split() if w not in forbidden and len(w) > 2]
        
        if clean_words:
            item = " ".join(clean_words) 
            if cell not in inventory: inventory[cell] = []
            if item not in inventory[cell]:
                inventory[cell].append(item); save_inventory()
                command_esp(f"/light?cell={cell}&r=0&g=150&b=255")
                add_log(f"Update: {item} -> {cell}")
                play_sound("success"); start_led_timer()
            return False
        else:
            command_esp(f"/light?cell={cell}&r=255&g=100&b=0")
            add_log(f"Visualizing sector {cell}")
            play_sound("success"); start_led_timer(); return False

    add_log(f"Команда не распознана: {text}", True)
    return False

# --- ВАЖНО: WEB API ДЛЯ ФРОНТЕНДА (ОНО ПРОПАЛО В ПРОШЛЫЙ РАЗ) ---
@app.route('/api/status')
def get_status():
    return jsonify({
        "inventory": inventory, 
        "logs": logs[-15:], 
        "errors": errors[-15:], 
        "esp_status": esp_connected
    })

@app.route('/api/command')
def api_command():
    if request.args.get('action') == 'off': 
        if led_timer: led_timer.cancel()
        command_esp("/off")
    return jsonify({"status": "ok"})
# -----------------------------------------------------------------

# --- ОБРАБОТКА АУДИО ---
def callback(indata, frames, time, status): q.put(bytes(indata))

def listen_command_google():
    """Записывает 5 секунд и отправляет в Google"""
    fs = 16000
    duration = 5
    try:
        time.sleep(0.2)
        rec_data = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16'); sd.wait()
        audio = sr.AudioData(rec_data.tobytes(), fs, 2)
        return sr.Recognizer().recognize_google(audio, language="ru-RU")
    except: return None

def main_loop():
    if not os.path.exists(MODEL_PATH): 
        print(f"ОШИБКА: Папка {MODEL_PATH} не найдена!")
        return
        
    print(">>> [SYSTEM] Загрузка нейропрофиля Vosk...")
    try:
        vosk_model = Model(MODEL_PATH)
    except Exception as e:
        print(f"!!! Ошибка загрузки модели Vosk: {e}")
        return

    add_log("Jarvis Core Online. All systems nominal.")
    play_sound("привет")
    command_esp("/off")

    print(">>> [SYSTEM] Запуск Flask API...")
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False), daemon=True).start()

    print("\n" + "="*40)
    print("ДЖАРВИС ГОТОВ. Жду активации...")
    print("="*40 + "\n")

    while True:
        try:
            # 1. РЕЖИМ ОЖИДАНИЯ (VOSK)
            with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16', channels=1, callback=callback):
                rec = KaldiRecognizer(vosk_model, 16000)
                activated = False
                while not activated:
                    data = q.get()
                    if rec.AcceptWaveform(data):
                        res = json.loads(rec.Result()).get("text", "")
                        if "джарвис" in res or "jarvis" in res: activated = True
            
            # 2. РЕЖИМ АКТИВНОЙ СЕССИИ (GOOGLE)
            if activated:
                play_sound("yessir")
                add_log("Сессия активирована. Слушаю...")
                
                session_end_time = time.time() + SESSION_TIME
                
                while time.time() < session_end_time:
                    cmd = listen_command_google()
                    
                    if cmd:
                        print(f"Обработка: {cmd}")
                        if "джарвис" in cmd.lower() and len(cmd.split()) < 3: 
                            play_sound("yessir")
                            session_end_time = time.time() + SESSION_TIME 
                            continue

                        add_log(f"Voice Command: '{cmd}'")
                        should_exit = process_intent(cmd)
                        
                        if should_exit: break
                        
                        session_end_time = time.time() + SESSION_TIME
                    else:
                        print(f"Тишина... До конца сессии: {int(session_end_time - time.time())} сек.")
                
                add_log("Сессия завершена. Переход в режим ожидания.")
                while not q.empty(): q.get()

        except Exception as e:
            print(f"Ошибка в основном цикле: {e}")
            time.sleep(1)

if __name__ == '__main__':
    try: main_loop()
    except KeyboardInterrupt: 
        if led_timer: led_timer.cancel()
        save_inventory(); sys.exit(0)