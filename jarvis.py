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
AUTO_OFF_TIME = 10.0 # Секунд до выключения

# --- ИНИЦИАЛИЗАЦИЯ ---
morph = pymorphy3.MorphAnalyzer()
app = Flask(__name__)
CORS(app)

logs, errors, inventory = [], [], {}
esp_connected = "OFFLINE"
q = queue.Queue()
led_timer = None 

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

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
            try: winsound.PlaySound(os.path.join(path, random.choice(files)), winsound.SND_FILENAME | winsound.SND_ASYNC)
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

# --- УЛУЧШЕННЫЙ МАППИНГ ЯЧЕЕК ---
def extract_cell(text):
    text = text.lower()
    mapping = {'a':'А', 'а':'А', 'b':'Б', 'б':'Б', 'v':'В', 'в':'В', 'w':'В', 'c':'В', 'с':'В', 'g':'Г', 'г':'Г', 'd':'Д', 'д':'Д'}
    # Ищем комбинацию буква + цифра
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
    
    # 1. КОМАНДА: ВЫКЛЮЧИТЬ
    if any(w in text for w in ["выключи", "погаси", "отключи", "пока"]):
        if led_timer: led_timer.cancel()
        command_esp("/off"); add_log("STANDBY Mode Active"); play_sound("пока"); return

    # 2. КОМАНДА: ОЧИСТКА ЯЧЕЙКИ ("Очисти ячейку А1")
    if "очист" in text or "удали все" in text:
        if cell:
            inventory[cell] = []
            save_inventory()
            command_esp(f"/light?cell={cell}&r=255&g=0&b=0")
            add_log(f"System: Сектор {cell} очищен")
            play_sound("yessir"); start_led_timer(); return
        else:
            add_log("Ошибка: Не указан сектор для очистки", True); return

    # 3. КОМАНДА: ДОБАВИТЬ [ПРЕДМЕТ] В [ЯЧЕЙКА]
    if "добав" in text or "положи" in text:
        # Ищем ячейку
        if cell:
            # Вырезаем предмет: всё, что между "добавь" и "в [ячейка]"
            # Пример: "добавь гайку в а1" -> "гайку"
            try:
                # Находим часть текста до слова "в" перед ячейкой
                parts = re.split(r'\s+в\s+', text)
                if len(parts) > 1:
                    item_raw = parts[0].split()[-1] # Слово непосредственно перед "в"
                else:
                    # Если "в" пропущено, берем слово перед названием ячейки
                    item_raw = text.replace("добавь", "").replace(cell.lower(), "").strip().split()[-1]
                
                item = morph.parse(item_raw)[0].normal_form
                if cell not in inventory: inventory[cell] = []
                if item not in inventory[cell]:
                    inventory[cell].append(item); save_inventory()
                    command_esp(f"/light?cell={cell}&r=0&g=150&b=255")
                    add_log(f"Update: {item} -> {cell}"); play_sound("yessir"); start_led_timer()
                return
            except:
                add_log("Ошибка: Не удалось распознать предмет", True); return

    # 4. КОМАНДА: УДАЛИТЬ ПРЕДМЕТ
    if "удали" in text or "убери" in text:
        if cell:
            # Логика поиска конкретного предмета в тексте
            words = text.split()
            for w in words:
                norm_w = morph.parse(w)[0].normal_form
                if cell in inventory and norm_w in inventory[cell]:
                    inventory[cell].remove(norm_w); save_inventory()
                    command_esp(f"/light?cell={cell}&r=255&g=0&b=0")
                    add_log(f"Modified: {norm_w} удален из {cell}")
                    play_sound("yessir"); start_led_timer(); return

    # 5. КОМАНДА: ПОИСК
    if any(w in text for w in ["где", "найди"]):
        found_cell = None
        for word in text.split():
            norm = morph.parse(word)[0].normal_form
            for c, items in inventory.items():
                if any(norm in morph.parse(it)[0].normal_form for it in items): found_cell = c
        if found_cell:
            command_esp(f"/light?cell={found_cell}&r=0&g=255&b=0")
            add_log(f"Locator: сектор {found_cell}")
            play_sound("yessir"); start_led_timer()
        else: add_log(f"Объект '{text}' не найден", True)
        return

    # 6. КОМАНДА: ПРОСТО ПОДСВЕТИТЬ (если названа только ячейка)
    if cell:
        command_esp(f"/light?cell={cell}&r=255&g=100&b=0")
        add_log(f"Visualizing sector {cell}"); play_sound("yessir"); start_led_timer(); return

    add_log(f"Команда не распознана: {text}", True)

# --- WEB API ---
@app.route('/api/status')
def get_status():
    return jsonify({"inventory": inventory, "logs": logs[-15:], "errors": errors[-15:], "esp_status": esp_connected})

@app.route('/api/command')
def api_command():
    if request.args.get('action') == 'off': 
        if led_timer: led_timer.cancel()
        command_esp("/off")
    return jsonify({"status": "ok"})

# --- ОБРАБОТКА АУДИО ---
def callback(indata, frames, time, status): q.put(bytes(indata))

def listen_command_google():
    fs = 16000
    duration = 5 # Увеличили до 5 секунд
    try:
        time.sleep(0.3) # Пауза, чтобы не записывать звук "Да, сэр"
        print("🔴 СЛУШАЮ КОМАНДУ...")
        rec_data = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16'); sd.wait()
        audio = sr.AudioData(rec_data.tobytes(), fs, 2)
        return sr.Recognizer().recognize_google(audio, language="ru-RU")
    except: return None

def main_loop():
    if not os.path.exists(MODEL_PATH): return
    vosk_model = Model(MODEL_PATH)
    add_log("Jarvis Core Online. Listening mode active.")
    play_sound("привет"); command_esp("/off")

    while True:
        try:
            with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16', channels=1, callback=callback):
                rec = KaldiRecognizer(vosk_model, 16000)
                activated = False
                while not activated:
                    data = q.get()
                    if rec.AcceptWaveform(data):
                        res = json.loads(rec.Result()).get("text", "")
                        if "джарвис" in res or "jarvis" in res: activated = True
            if activated:
                play_sound("yessir")
                cmd = listen_command_google()
                if cmd: 
                    add_log(f"Voice Command: '{cmd}'")
                    process_intent(cmd)
                else: add_log("Voice engine timeout", True)
                while not q.empty(): q.get()
        except Exception as e:
            print(f"Loop restart: {e}"); time.sleep(1)

if __name__ == '__main__':
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000), daemon=True).start()
    try: main_loop()
    except KeyboardInterrupt: 
        if led_timer: led_timer.cancel()
        save_inventory(); sys.exit(0)