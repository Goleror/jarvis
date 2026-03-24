#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <Adafruit_NeoPixel.h>

// --- НАСТРОЙКИ ---
const char* ssid = "ТВОЙ_WIFI";       // Укажи свой Wi-Fi
const char* password = "ТВОЙ_ПАРОЛЬ";   // Укажи пароль

#define PIN 12        // Пин подключения ленты (12 = D6 на NodeMCU)
#define NUMPIXELS 90  // 45 диодов (1 модуль) + 45 диодов (2 модуль) = 90

Adafruit_NeoPixel strip = Adafruit_NeoPixel(NUMPIXELS, PIN, NEO_GRB + NEO_KHZ800);
ESP8266WebServer server(80);

// --- МАТЕМАТИКА ВЫЧИСЛЕНИЯ ЯЧЕЙКИ ---
int getLedIndex(String cell) {
  int row = -1;
  int col = -1;

  // 1. Ищем ряд (строку) по русской или английской букве
  if (cell.indexOf("А") != -1 || cell.indexOf("A") != -1) row = 0;
  else if (cell.indexOf("Б") != -1 || cell.indexOf("B") != -1) row = 1;
  else if (cell.indexOf("В") != -1 || cell.indexOf("V") != -1) row = 2;
  else if (cell.indexOf("Г") != -1 || cell.indexOf("G") != -1) row = 3;
  else if (cell.indexOf("Д") != -1 || cell.indexOf("D") != -1) row = 4;

  if (row == -1) return -1; // Буква не найдена

  // 2. Ищем колонку (извлекаем все цифры из строки)
  String numStr = "";
  for (int i = 0; i < cell.length(); i++) {
    if (isDigit(cell[i])) {
      numStr += cell[i];
    }
  }
  col = numStr.toInt();

  if (col < 1 || col > 10) return -1; // Если цифра вне диапазона

  // 3. Вычисляем индекс светодиода
  int index = 0;
  if (col <= 5) {
    // Первый модуль (Колонки 1-5)
    index = (row * 9) + ((col - 1) * 2);
  } else {
    // Второй модуль (Колонки 6-10) - смещение на 45 диодов
    index = 45 + (row * 9) + ((col - 6) * 2);
  }
  
  return index;
}

// --- ОБРАБОТЧИКИ КОМАНД ОТ PYTHON ---
void handleLight() {
  if (!server.hasArg("cell")) {
    server.send(400, "text/plain", "Missing cell");
    return;
  }
  
  String cell = server.arg("cell");
  int r = server.hasArg("r") ? server.arg("r").toInt() : 0;
  int g = server.hasArg("g") ? server.arg("g").toInt() : 0;
  int b = server.hasArg("b") ? server.arg("b").toInt() : 0;

  int ledIndex = getLedIndex(cell);

  if (ledIndex >= 0 && ledIndex < NUMPIXELS) {
    strip.clear(); // Выключаем все диоды
    strip.setPixelColor(ledIndex, strip.Color(r, g, b)); // Зажигаем нужный
    strip.show();
    server.send(200, "text/plain", "OK LED: " + String(ledIndex));
  } else {
    server.send(400, "text/plain", "Invalid cell mapping");
  }
}

void handleOff() {
  strip.clear();
  strip.show();
  server.send(200, "text/plain", "OK OFF");
}

// --- СТАРТ СИСТЕМЫ ---
void setup() {
  Serial.begin(115200);
  
  // Инициализация ленты
  strip.begin();
  strip.clear();
  strip.show();

  // Подключение к Wi-Fi
  Serial.print("Connecting to Wi-Fi");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("\nWiFi connected!");
  Serial.print("ESP IP Address: ");
  Serial.println(WiFi.localIP());

  // Настройка путей
  server.on("/light", handleLight);
  server.on("/off", handleOff);
  server.begin();
  Serial.println("HTTP server started");
}

void loop() {
  server.handleClient();
}