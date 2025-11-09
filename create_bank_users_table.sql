-- SQL скрипт для создания таблицы bank_users
-- Выполните этот скрипт в вашей базе данных, если таблица еще не создана

CREATE TABLE IF NOT EXISTS bank_users (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    bank_code VARCHAR(50) NOT NULL,
    bank_user_id VARCHAR(255) NOT NULL,
    consent_id VARCHAR(255),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_bank_users_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT unique_user_bank UNIQUE (user_id, bank_code)
);

-- Создаем индекс для быстрого поиска по user_id
CREATE INDEX IF NOT EXISTS ix_bank_users_user_id ON bank_users(user_id);

-- Комментарии к таблице
COMMENT ON TABLE bank_users IS 'Хранит ID пользователей в банках и их consent_id';
COMMENT ON COLUMN bank_users.user_id IS 'ID пользователя в нашем приложении';
COMMENT ON COLUMN bank_users.bank_code IS 'Код банка (vbank, abank, sbank)';
COMMENT ON COLUMN bank_users.bank_user_id IS 'ID пользователя в банке (вводит пользователь)';
COMMENT ON COLUMN bank_users.consent_id IS 'ID согласия (получается автоматически при запросе счетов)';

