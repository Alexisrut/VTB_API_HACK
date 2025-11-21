# Тестирование функции создания нового банка

## Новые endpoints

### 1. POST `/api/v1/users/me/banks` - Создание нового банка

**Описание:** Создает новый банк для пользователя с указанной конфигурацией.

**Требования:**
- Аутентификация (токен в заголовке `Authorization: Bearer <token>`)

**Тело запроса:**
```json
{
  "bank_code": "mybank",
  "bank_name": "My Bank",
  "use_standard_url": true,
  "api_url": null,
  "bank_user_id": "team261-1"
}
```

**Параметры:**
- `bank_code` (string, обязательный) - Уникальный код банка (только латиница, цифры, дефисы, подчеркивания, минимум 3 символа)
- `bank_name` (string, обязательный) - Отображаемое имя банка
- `use_standard_url` (boolean, по умолчанию true) - Использовать стандартный URL `https://{bank_code}.open.bankingapi.ru`
- `api_url` (string, опциональный) - Кастомный URL (требуется если `use_standard_url=false`)
- `bank_user_id` (string, обязательный) - ID пользователя в банке

**Примеры запросов:**

#### Пример 1: Создание банка со стандартным URL
```bash
curl -X POST "http://localhost:8000/api/v1/users/me/banks" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "bank_code": "testbank",
    "bank_name": "Test Bank",
    "use_standard_url": true,
    "bank_user_id": "team261-1"
  }'
```

#### Пример 2: Создание банка с кастомным URL
```bash
curl -X POST "http://localhost:8000/api/v1/users/me/banks" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "bank_code": "custombank",
    "bank_name": "Custom Bank",
    "use_standard_url": false,
    "api_url": "https://custom-bank.example.com",
    "bank_user_id": "team261-1"
  }'
```

**Успешный ответ (200):**
```json
{
  "bank_code": "testbank",
  "bank_name": "Test Bank",
  "api_url": "https://testbank.open.bankingapi.ru",
  "bank_user_id": "team261-1",
  "has_consent": false,
  "consent_status": null
}
```

**Ошибки:**
- `400` - Банк с таким кодом уже существует
- `400` - Банк недоступен (валидация не прошла)
- `400` - Ошибка валидации полей
- `500` - Внутренняя ошибка сервера

---

### 2. GET `/api/v1/users/me/banks` - Получение списка банков пользователя

**Описание:** Возвращает список всех банков пользователя с их конфигурациями и статусами согласий.

**Требования:**
- Аутентификация (токен в заголовке `Authorization: Bearer <token>`)

**Пример запроса:**
```bash
curl -X GET "http://localhost:8000/api/v1/users/me/banks" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Успешный ответ (200):**
```json
{
  "banks": [
    {
      "bank_code": "vbank",
      "bank_name": "Virtual Bank",
      "api_url": "https://vbank.open.bankingapi.ru",
      "bank_user_id": "team261-1",
      "has_consent": true,
      "consent_status": "approved"
    },
    {
      "bank_code": "testbank",
      "bank_name": "Test Bank",
      "api_url": "https://testbank.open.bankingapi.ru",
      "bank_user_id": "team261-1",
      "has_consent": false,
      "consent_status": null
    }
  ]
}
```

---

## Пошаговое тестирование

### Шаг 1: Получить токен доступа

```bash
# Войдите в систему и получите access_token
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your@email.com",
    "password": "your_password"
  }'
```

Сохраните `access_token` из ответа.

### Шаг 2: Проверить текущие банки

```bash
curl -X GET "http://localhost:8000/api/v1/users/me/banks" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Должен вернуться список существующих банков (vbank, abank, sbank, если они настроены).

### Шаг 3: Создать новый банк

```bash
curl -X POST "http://localhost:8000/api/v1/users/me/banks" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "bank_code": "testbank",
    "bank_name": "Test Bank",
    "use_standard_url": true,
    "bank_user_id": "team261-1"
  }'
```

**Ожидаемый результат:**
- Создается запись в таблице `bank_configs`
- Создается запись в таблице `bank_users`
- Возвращается информация о созданном банке

### Шаг 4: Проверить создание в БД

```sql
-- Проверить конфигурацию банка
SELECT * FROM bank_configs WHERE bank_code = 'testbank';

-- Проверить bank_user
SELECT * FROM bank_users WHERE bank_code = 'testbank';
```

### Шаг 5: Повторно получить список банков

```bash
curl -X GET "http://localhost:8000/api/v1/users/me/banks" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Новый банк должен появиться в списке.

### Шаг 6: Создать согласие для нового банка

```bash
curl -X POST "http://localhost:8000/api/v1/banks/account-consents?bank_code=testbank" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Шаг 7: Получить счета нового банка

```bash
curl -X GET "http://localhost:8000/api/v1/banks/accounts/all" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Новые счета должны появиться в ответе.

---

## Тестирование валидации

### Тест 1: Дубликат bank_code
```bash
# Попытка создать банк с уже существующим кодом
curl -X POST "http://localhost:8000/api/v1/users/me/banks" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "bank_code": "vbank",
    "bank_name": "Duplicate Bank",
    "use_standard_url": true,
    "bank_user_id": "team261-1"
  }'
```

**Ожидаемый результат:** `400 Bad Request` с сообщением о том, что банк уже существует.

### Тест 2: Неверный формат bank_code
```bash
curl -X POST "http://localhost:8000/api/v1/users/me/banks" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "bank_code": "test bank",
    "bank_name": "Test Bank",
    "use_standard_url": true,
    "bank_user_id": "team261-1"
  }'
```

**Ожидаемый результат:** `422 Validation Error` - пробелы не допускаются.

### Тест 3: Недоступный банк
```bash
curl -X POST "http://localhost:8000/api/v1/users/me/banks" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "bank_code": "nonexistent",
    "bank_name": "Nonexistent Bank",
    "use_standard_url": true,
    "bank_user_id": "team261-1"
  }'
```

**Ожидаемый результат:** `400 Bad Request` - банк недоступен (валидация не прошла).

### Тест 4: Кастомный URL без указания
```bash
curl -X POST "http://localhost:8000/api/v1/users/me/banks" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "bank_code": "custombank",
    "bank_name": "Custom Bank",
    "use_standard_url": false,
    "bank_user_id": "team261-1"
  }'
```

**Ожидаемый результат:** `400 Bad Request` - требуется указать api_url.

---

## Проверка работы с существующими банками

После создания нового банка убедитесь, что:
1. ✅ Можно создать согласие для нового банка
2. ✅ Можно получить счета нового банка
3. ✅ Можно получить балансы нового банка
4. ✅ Можно получить транзакции нового банка
5. ✅ Новый банк отображается в списке всех счетов (`/api/v1/banks/accounts/all`)

---

## Отладка

Если что-то не работает:

1. **Проверьте логи сервера:**
   ```bash
   tail -f logs/app.log
   ```

2. **Проверьте БД:**
   ```sql
   SELECT * FROM bank_configs ORDER BY created_at DESC;
   SELECT * FROM bank_users ORDER BY created_at DESC;
   ```

3. **Проверьте валидацию банка:**
   ```bash
   # Попробуйте получить токен для банка напрямую
   curl -X POST "https://testbank.open.bankingapi.ru/auth/bank-token?client_id=team261&client_secret=24ADfpV1IyoAAP7d"
   ```

---

## Примечания

- Стандартные credentials используются для всех банков:
  - `client_id`: "team261-3"
  - `client_secret`: "24ADfpV1IyoAAP7d"
  - `requesting_bank`: "team261"

- При создании банка автоматически создается `bank_user` для текущего пользователя.

- Валидация банка происходит через попытку получения access token от API банка.

