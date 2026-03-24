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
AUTO_OFF_TIME = 10.0 
SESSION_TIME = 15.0   

SYNONYMS = {
    "тест": "test", "test": "тест",
    "ардуино": "arduino", "arduino": "ардуино",
    "кабель": "cable", "cable": "кабель",
    "нож": "knife", "knife": "нож"
}

morph = pymorphy3.MorphAnalyzer()
app = Flask(__name__)
CORS(app)

logs, errors, inventory = [], [], {}
esp_connected = "OFFLINE"
q = queue.Queue()
led_timer = None 
last_action = {"cell": None, "time": 0} 

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

def update_last_action(cell):
    global last_action
    last_action = {"cell": cell, "time": time.time()}

def auto_off_action():
    if command_esp("/off"): add_log("System: Авто-выключение индикации")

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

# --- ДОБАВЛЕНЫ ЦИФРЫ ДО 10 ---
NUMBERS = {
    "один":"1", "1":"1", "два":"2", "2":"2", "три":"3", "3":"3", "четыре":"4", "4":"4", "пять":"5", "5":"5",
    "шесть":"6", "6":"6", "семь":"7", "7":"7", "восемь":"8", "8":"8", "девять":"9", "9":"9", "десять":"10", "10":"10"
}

def extract_cell(text):
    text = text.lower()
    mapping = {'a':'А', 'а':'А', 'b':'Б', 'б':'Б', 'v':'В', 'в':'В', 'w':'В', 'c':'В', 'с':'В', 'g':'Г', 'г':'Г', 'd':'Д', 'д':'Д'}
    # Ищем от 1 до 10
    match = re.search(r'([а-дa-eвvbcg])\s*([1-9]|10)', text)
    if match:
        l = mapping.get(match.group(1), match.group(1).upper())
        return f"{l}{match.group(2)}"
    
    # Если сказал словами (например "Б шесть")
    words = text.split()
    for i, w in enumerate(words):
        if w in mapping or w in "абвгд":
            if i + 1 < len(words) and words[i+1] in NUMBERS:
                return f"{mapping.get(w, w.upper())}{NUMBERS[words[i+1]]}"
    return None

def words_match(search_word, target_word):
    search_word, target_word = search_word.lower().strip(), target_word.lower().strip()
    if search_word == target_word or search_word in target_word or target_word in search_word: return True
    s_norm = morph.parse(search_word)[0].normal_form
    t_norm = morph.parse(target_word)[0].normal_form
    if s_norm == t_norm: return True
    if SYNONYMS.get(s_norm) == t_norm or SYNONYMS.get(t_norm) == s_norm: return True
    return False

def process_intent(text):
    global led_timer
    text = text.lower()
    cell = extract_cell(text)
    
    if any(w in text for w in ["выключи", "погаси", "отключи", "пока"]):
        if led_timer: led_timer.cancel()
        command_esp("/off"); add_log("STANDBY Mode Active"); play_sound("succes"); return True

    if "очист" in text or "удали все" in text:
        if cell:
            inventory[cell] = []
            save_inventory(); command_esp(f"/light?cell={cell}&r=255&g=0&b=0")
            add_log(f"System: Сектор {cell} очищен"); play_sound("succes"); start_led_timer(); update_last_action(cell); return False

    if any(w in text for w in ["где", "найди", "покажи"]):
        found_cell = None
        query_words = [w for w in text.split() if w not in ["где", "найди", "покажи", "джарвис", "лежит", "находится"]]
        for c, items in inventory.items():
            for item in items:
                for qw in query_words:
                    if words_match(qw, item): found_cell = c; break
            if found_cell: break
        if found_cell:
            command_esp(f"/light?cell={found_cell}&r=0&g=255&b=0")
            add_log(f"Locator: сектор {found_cell}"); play_sound("succes"); start_led_timer(); update_last_action(found_cell); return False
        else: add_log(f"Объект не найден", True); return False

    if "удали" in text or "убери" in text:
        if cell:
            words = text.split()
            for item in inventory.get(cell, []):
                for w in words:
                    if words_match(w, item):
                        inventory[cell].remove(item); save_inventory(); command_esp(f"/light?cell={cell}&r=255&g=0&b=0")
                        add_log(f"Modified: {item} удален"); play_sound("succes"); start_led_timer(); update_last_action(cell); return False

    if cell:
        forbidden = ["джарвис", "ячейка", "личинка", "добавь", "запиши", "в", "на", "сектор", cell.lower()]
        clean_words = [w for w in text.split() if w not in forbidden and len(w) > 2 and not (len(w)==1 and w in "абвгд")]
        if clean_words:
            item = " ".join(clean_words) 
            if cell not in inventory: inventory[cell] = []
            if item not in inventory[cell]:
                inventory[cell].append(item); save_inventory(); command_esp(f"/light?cell={cell}&r=0&g=150&b=255")
                add_log(f"Update: {item} -> {cell}"); play_sound("succes"); start_led_timer(); update_last_action(cell)
            return False
        else:
            command_esp(f"/light?cell={cell}&r=255&g=100&b=0")
            add_log(f"Visualizing sector {cell}"); play_sound("succes"); start_led_timer(); update_last_action(cell); return False

    add_log(f"Команда не распознана: {text}", True); return False

@app.route('/api/status')
def get_status():
    return jsonify({"inventory": inventory, "logs": logs[-15:], "errors": errors[-15:], "esp_status": esp_connected, "last_action": last_action})

@app.route('/api/command')
def api_command():
    if request.args.get('action') == 'off': 
        if led_timer: led_timer.cancel()
        command_esp("/off")
    return jsonify({"status": "ok"})

def callback(indata, frames, time, status): q.put(bytes(indata))

def listen_command_google():
    fs = 16000
    try:
        time.sleep(0.3); rec_data = sd.rec(int(5 * fs), samplerate=fs, channels=1, dtype='int16'); sd.wait()
        audio = sr.AudioData(rec_data.tobytes(), fs, 2)
        return sr.Recognizer().recognize_google(audio, language="ru-RU")
    except: return None

def main_loop():
    if not os.path.exists(MODEL_PATH): return
    print(">>> [SYSTEM] Загрузка Vosk...")
    vosk_model = Model(MODEL_PATH)
    add_log("Jarvis Core Online. All systems nominal.")
    play_sound("привет"); command_esp("/off")
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False), daemon=True).start()

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
                session_end = time.time() + SESSION_TIME
                while time.time() < session_end:
                    cmd = listen_command_google()
                    if cmd:
                        if "джарвис" in cmd.lower() and len(cmd.split()) < 3: 
                            play_sound("yessir"); session_end = time.time() + SESSION_TIME; continue
                        add_log(f"Voice Command: '{cmd}'")
                        if process_intent(cmd): break
                        session_end = time.time() + SESSION_TIME
                while not q.empty(): q.get()
        except Exception as e:
            print(f"Restart: {e}"); time.sleep(1)

if __name__ == '__main__':
    try: main_loop()
    except KeyboardInterrupt: 
        if led_timer: led_timer.cancel()
        save_inventory(); sys.exit(0)