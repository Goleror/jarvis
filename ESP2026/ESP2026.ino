#include <ESP8266WiFi.h>      // Библиотека WiFi для ESP8266
#include <ESP8266WebServer.h> // Библиотека WebServer для ESP8266
#include <Adafruit_NeoPixel.h>
#include <map>      

// --- КОНФИГУРАЦИЯ WI-FI ---
const char* ssid = "VlessWB2WFtre";         // ВАШЕ ИМЯ WI-FI СЕТИ
const char* password = "rQyyrztMyS4G!"; // ВАШ ПАРОЛЬ ОТ WI-FI
          // Для использования std::map


// --- КОНФИГУРАЦИЯ NEOPIXEL ---
// D6 на плате NodeMCU V3 соответствует GPIO12.
#define LED_PIN    12   // Пин ESP8266 (GPIO12, соответствует D6 на плате).
#define LED_COUNT  45   // Общее количество светодиодов на ленте.

// Обратите внимание на тип NEO_GRB. Некоторые ленты могут быть NEO_RGB.
// Если цвета перепутаны (например, просите красный, а горит зеленый),
// попробуйте изменить на NEO_RGB + NEO_KHZ800.
Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

ESP8266WebServer server(80); // HTTP-сервер на порту 80

// --- MAP ЯЧЕЙКА -> ИНДЕКС СВЕТОДИОДА ---
std::map<String, int> cellToLedIndex = {
    {"А1", 0}, {"А2", 2}, {"А3", 4}, {"А4", 6}, {"А5", 8},
    {"Б1", 9}, {"Б2", 11}, {"Б3", 13}, {"Б4", 15}, {"Б5", 17},
    {"В1", 18}, {"В2", 20}, {"В3", 22}, {"В4", 24}, {"В5", 26},
    {"Г1", 27}, {"Г2", 29}, {"Г3", 31}, {"Г4", 33}, {"Г5", 35},
    {"Д1", 36}, {"Д2", 38}, {"Д3", 40}, {"Д4", 42}, {"Д5", 44}
};

// --- ФУНКЦИЯ ОБРАБОТКИ ЗАПРОСА ДЛЯ ПОДСВЕТКИ ОДНОЙ ЯЧЕЙКИ ---
void handleLightCell() {
  String cell = server.arg("cell"); // Получаем название ячейки (например, "А1")
  int r = server.hasArg("r") ? server.arg("r").toInt() : 0;
  int g = server.hasArg("g") ? server.arg("g").toInt() : 0;
  int b = server.hasArg("b") ? server.arg("b").toInt() : 0;

  if (cellToLedIndex.count(cell)) {
    int ledIndex = cellToLedIndex[cell];
    
    // Очищаем все светодиоды перед подсветкой
    strip.clear(); 

    strip.setPixelColor(ledIndex, strip.Color(r, g, b));
    strip.show();
    server.send(200, "text/plain", "OK: Cell " + cell + " lit. IP: " + WiFi.localIP().toString());
  } else {
    server.send(400, "text/plain", "Error: Invalid cell name.");
  }
}

// --- ФУНКЦИЯ ОБРАБОТКИ ЗАПРОСА ДЛЯ ВЫКЛЮЧЕНИЯ ВСЕХ СВЕТОДИОДОВ ---
void handleOff() {
  strip.clear();
  strip.show();
  server.send(200, "text/plain", "OK: All LEDs turned off. IP: " + WiFi.localIP().toString());
}

// --- ФУНКЦИЯ ОБРАБОТКИ НЕИЗВЕСТНЫХ ЗАПРОСОВ ---
void handleNotFound() {
  server.send(404, "text/plain", "Not Found");
}

void setup() {
  Serial.begin(115200);

  // Инициализация NeoPixel
  strip.begin();
  strip.show(); // Инициализация всех светодиодов в выключенном состоянии

  // Подключение к Wi-Fi
  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  int attempts = 0;
  // ESP8266 иногда нужно больше времени для подключения, увеличим попытки
  while (WiFi.status() != WL_CONNECTED && attempts < 40) { // 40 попыток * 0.5 сек = 20 секунд
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("");
    Serial.println("WiFi connected");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());

    // Настройка маршрутов HTTP-сервера
    server.on("/light", HTTP_GET, handleLightCell);
    server.on("/off", HTTP_GET, handleOff);
    server.onNotFound(handleNotFound);

    server.begin(); // Запуск сервера
    Serial.println("HTTP server started");
  } else {
    Serial.println("");
    Serial.println("Failed to connect to WiFi. Please check SSID/Password. Trying again in 5 seconds...");
    delay(5000);
    ESP.restart(); // Перезагружаем ESP8266, чтобы попробовать подключиться снова
  }
}

void loop() {
  server.handleClient(); // Обработка входящих HTTP-запросов
}