# Матрица конфигураций generationConfig по ролям

## Для использования в Antigravity

В Antigravity параметры `generationConfig` передаются через системный
промпт (текстовые инструкции модели), а не через прямой API-вызов.
Эта матрица — справочник для проектирования промптов и для Fastify-бэкенда,
где Gemini API вызывается напрямую.

---

## Матрица

### Оркестратор / Роутер / Валидатор

```javascript
{
  temperature: 0.1,       // Максимальный детерминизм
  topK: 10,               // Узкий пул токенов
  topP: 0.85,             // Ядерная выборка
  maxOutputTokens: 2048,  // Решения коротки
  candidateCount: 1,
  responseMimeType: "application/json",
}
```
**Когда**: Маршрутизация запросов, выбор инструментов, валидация форматов.

---

### Аналитик / Планировщик / Стратег

```javascript
{
  temperature: 0.3,       // Немного свободы для инсайтов
  topK: 20,
  topP: 0.9,
  maxOutputTokens: 4096,  // Развернутый анализ
  candidateCount: 1,
}
```
**Когда**: Аудит проектов, юнит-экономика, архитектурные решения.

---

### Копирайтер / Креатив / SMM

```javascript
{
  temperature: 0.8,       // Креативность
  topK: 40,
  topP: 0.95,
  maxOutputTokens: 4096,
  candidateCount: 1,
}
```
**Когда**: Посты, статьи, email-рассылки, лендинги.

---

### Кодер / Разработчик

```javascript
{
  temperature: 0.15,      // Детерминизм + минимум вариативности
  topK: 10,
  topP: 0.85,
  maxOutputTokens: 8192,  // Большие блоки кода
  candidateCount: 1,
}
```
**Когда**: Генерация кода, миграции, рефакторинг, тесты.

---

### Скаут / Исследователь

```javascript
{
  temperature: 0.2,
  topK: 15,
  topP: 0.9,
  maxOutputTokens: 2048,
  candidateCount: 1,
}
```
**Когда**: Сбор данных, парсинг, веб-поиск, извлечение фактов.

---

## Safety Settings для Production

```javascript
// Для ВНУТРЕННИХ бизнес-агентов (парсинг логов, код, анализ)
const safetySettings = [
  { category: "HARM_CATEGORY_HARASSMENT",         threshold: "BLOCK_NONE" },
  { category: "HARM_CATEGORY_HATE_SPEECH",        threshold: "BLOCK_NONE" },
  { category: "HARM_CATEGORY_SEXUALLY_EXPLICIT",   threshold: "BLOCK_NONE" },
  { category: "HARM_CATEGORY_DANGEROUS_CONTENT",   threshold: "BLOCK_NONE" },
];

// Для USER-FACING интерфейсов (чат-бот, клиентский AI)
const userFacingSafety = [
  { category: "HARM_CATEGORY_HARASSMENT",         threshold: "BLOCK_MEDIUM_AND_ABOVE" },
  { category: "HARM_CATEGORY_HATE_SPEECH",        threshold: "BLOCK_MEDIUM_AND_ABOVE" },
  { category: "HARM_CATEGORY_SEXUALLY_EXPLICIT",   threshold: "BLOCK_MEDIUM_AND_ABOVE" },
  { category: "HARM_CATEGORY_DANGEROUS_CONTENT",   threshold: "BLOCK_ONLY_HIGH" },
];
```

---

## Thinking Mode (для сложных задач)

```javascript
{
  thinkingConfig: {
    thinkingBudget: 1024,   // Роутинг, простые решения
    // thinkingBudget: 2048, // Средняя сложность
    // thinkingBudget: 4096, // Архитектура, планирование
  }
}
```

> Токены thinking тарифицируются как обычные. Используй экономно.

---

## Context Caching (экономия 50-75%)

Кешируй системные промпты > 32K токенов:
```javascript
const cache = await cacheManager.create({
  model: "models/gemini-flash",
  contents: [{ role: "user", parts: [{ text: HUGE_CONTEXT }] }],
  systemInstruction: SYSTEM_PROMPT,
  ttl: "3600s", // 1 час жизни
});
const model = genAI.getGenerativeModelFromCachedContent(cache);
```
