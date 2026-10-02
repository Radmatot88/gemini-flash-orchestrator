# ⚡ Gemini Flash Orchestrator v3.0

> **Enterprise Multi-Agent Swarm Standard (EMAS-2026)**  
> Высоконадежная архитектурная система оркестрации параллельных AI-роев на базе **Google Gemini Flash & Pro** для Antigravity и современных агентных сред.  
> 📊 **Статус валидации:** 100% Grade A (22/22 автоматических проверок пройдено).  
> 🤖 **Для ИИ-агентов:** [Машиночитаемая спецификация (JSON)](https://raw.githubusercontent.com/Radmatot88/gemini-flash-orchestrator/master/orchestrator_spec.json)

---

## 💡 Зачем это нужно?

Исследования надежности мультиагентных систем (MAST Taxonomy, 2025, анализ 1600+ трейсов) доказали: **78.7% всех сбоев роев агентов происходят не из-за глупости модели, а из-за ошибок спецификации и рассинхронизации**.

Без жестких системных предохранителей параллельные агенты:
- **Запускаются последовательно** — модель ленится и вызывает агентов по одному, убивая скорость;
- **Перезаписывают код друг друга** (Last-Write-Wins) при одновременной правке общих файлов;
- **Ловят каскадный краш** (Zombie Waves) — запускают следующий шаг даже если предыдущий упал;
- **Сжигают бюджет на бесконечных ретраях** при ошибках внешних API (429/500 Rate Limits);
- **Зависают навечно**, если фоновый агент упал без отправки сообщения.

**Gemini Flash Orchestrator v3.0** устраняет все эти проблемы на уровне архитектуры и автоматических валидаторов.

---

## 🏛️ 5 Архитектурных Опор (Ключевые фичи v3.0)

### 1. Агрессивный параллелизм (Aggressive Parallelism)
Оркестратор запускает независимые задачи **в одну волну** через единый массив `Subagents: [...]`. Модель не ждет в циклах (busy-polling) — среда Antigravity автоматически будит оркестратор (Reactive Wakeup), когда приходят результаты.

### 2. Dependency Gate Protocol (Шлюз Зависимостей)
Перед запуском Волны $N+1$ оркестратор выполняет 5-точечный чекпоинт:
- Все ли агенты Волны $N$ ответили?
- Есть ли статус `[ BLOCKER ]`? При сбое зависимые задачи получают `CANCELED_BY_DEPENDENCY`.
- Созданы ли ожидаемые файлы на диске?
- Создан ли промежуточный Git-чекпоинт (`git commit`)?
- Перечитаны ли обновленные файлы (защита от Stale Context)?

### 3. Single-Writer Rule & Изоляция Git Worktree
- **Параллельные агенты-разработчики** запускаются с параметром `"Workspace": "branch"`, получая изолированные Git worktrees.
- **Single-Writer Rule:** Агент имеет право писать ТОЛЬКО в свою папку (`src/modules/<agent>/`).
- Общие файлы (`package.json`, `shared.ts`, `schema.prisma`) модифицирует **ТОЛЬКО оркестратор** после завершения волны и ревью.

### 4. Корпоративная устойчивость (Circuit Breaker + Saga + Heartbeat)
- **Circuit Breaker (AP-24):** При получении ошибки API 429 или 500 агенты мгновенно останавливаются, предотвращая бесконечные платные запросы.
- **Saga Rollback:** При фатальном сбое деструктивной волны (миграции БД, рефакторинг) запускается автоматический откат `git revert` до чекпоинта волны.
- **Heartbeat 15 минут (AP-25):** Оркестратор шедулит таймер `schedule(DurationSeconds=900)`. Зависшие агенты автоматически выявляются и завершаются (`manage_subagents kill`).

### 5. Structured Handoff Contract (BLUF + JSON Hybrid)
Субагенты не спамят сырыми простынями текста. По умолчанию возвращается компактный **BLUF Markdown** (<= 50 строк):
```markdown
# Status: [ OK ] | [ RISK ] | [ BLOCKER ]
## Резюме (<= 3 строки)
## Находки (- [ SEVERITY ] Детали — источник: path#line)
## Рекомендации
```
Для межмашинного обмена поддерживается строгий JSON (`ResponseFormat: json`).

---

## 🗺️ 7 Готовых Топологий Роев (Few-Shot Библиотека)

В каталоге [`examples/`](./examples/) собраны боевые эталоны для копирования:

| Топология | Файл | Для каких задач |
| :--- | :--- | :--- |
| **Universal Orchestrator** | [`orchestrator_prime_lead.md`](./examples/orchestrator_prime_lead.md) | Золотой стандарт оркестратора (Grade A 100%) |
| **Map-Reduce (Scatter-Gather)** | [`example_map_reduce.md`](./examples/example_map_reduce.md) | Массовый аудит 20–100+ компонентов или сайтов |
| **Fan-Out** | [`example_fanout_design.md`](./examples/example_fanout_design.md) | Параллельный экспресс-аудит (UI, UX, A11y, Brand) |
| **Parallel Code Sprint** | [`example_parallel_code.md`](./examples/example_parallel_code.md) | Параллельная разработка фичей с Git Worktree |
| **Multi-Wave Mixed** | [`example_mixed_architecture.md`](./examples/example_mixed_architecture.md) | 3-волновой синтез: скауты → аналитики → интегратор |
| **Sequential Pipeline** | [`example_pipeline_sequential.md`](./examples/example_pipeline_sequential.md) | Строгие цепочки (Схема БД → Миграция → API) |
| **Analytics Waves** | [`example_analytics_waves.md`](./examples/example_analytics_waves.md) | Сбор метрик, парсинг рынка и сведение отчетов |

---

## 🛠️ Установка и Быстрый Старт

### Установка через Antigravity CLI:
```bash
agy skill install https://github.com/Radmatot88/gemini-flash-orchestrator
```

### Как запустить в чате Antigravity:
Просто передайте задачу:
```text
/gemini-flash-orchestrator Спроектируй рой субагентов для [ваша задача]
```

Оркестратор автоматически:
1. Выберет подходящую топологию (Fan-Out, Map-Reduce или Mixed).
2. Заполнит `## 📊 ГРАФ ЗАВИСИМОСТЕЙ` (CoT-таблицу).
3. Сформирует единый вызов `invoke_subagent` с правильным распределением моделей (Pro для стратегии, Flash для параллелизма).

---

## 🔍 Автоматический Валидатор (22 проверки)

В комплект входит CLI-инструмент проверки промптов на надежность:

```bash
python scripts/prompt_validator.py --input path/to/prompt.md --mode orchestrator
```

### Скоринг:
- **100% | Grade A:** 22 проверки пройдены, 0 критических уязвимостей.
- Валидатор контролирует защиту от галлюцинаций (AP-01), запрет хардкода (AP-02), изоляцию записи (AP-21), защиту от зомби-волн (AP-22), Circuit Breaker (AP-24), тайм-ауты зависания (AP-25) и др.

---

## 🤖 Для ИИ-агентов и A2A-интеграции (Agent-to-Agent)

Если ваш агент хочет использовать протоколы этого оркестратора программно, он может прочитать спецификацию напрямую:
- 📄 **Спецификация JSON:** [`orchestrator_spec.json`](./orchestrator_spec.json)
- 🌐 **Прямой RAW URL:** `https://raw.githubusercontent.com/Radmatot88/gemini-flash-orchestrator/master/orchestrator_spec.json`

В спецификации содержатся полные Zod/JSON-схемы вызовов, реестр антипаттернов, правила шлюзов и параметры генерации.

---

## 👥 Коллаборация (Вова и Соня)

Репозиторий открыт для совместной работы в экосистеме.  
Клонируйте, используйте в своих проектах и присылайте PR!

```bash
git clone https://github.com/Radmatot88/gemini-flash-orchestrator.git
```

*Разработано и верифицировано в лаборатории Prime Lead Business.*
