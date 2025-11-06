import React, { useState } from "react";
import { Formik, Form, Field, ErrorMessage } from "formik";
import styles from "./AuthForm.module.scss";
import { Button } from "../../ui/button";
import { toast } from "sonner";
import * as api from "../../utils/api";
import { setCookie } from "../../utils/cookies";

type View = "login" | "register" | "verify";

interface AuthFormProps {
  onClose: () => void;
}

export const AuthForm: React.FC<AuthFormProps> = ({ onClose }) => {
  const [view, setView] = useState<View>("login");
  
  const [phoneForVerify, setPhoneForVerify] = useState("");

  const handleLogin = async (values: any, { setSubmitting }: any) => {
    try {
      const { data } = await api.login(values.email, values.password);
      setCookie("access_token", data.access_token, 15 / (24 * 60));
      setCookie("refresh_token", data.refresh_token, 7);
      toast.success("Вход выполнен успешно!");
      onClose();
      // Тут можно обновить стейт приложения (e.g., refetch user)
    } catch (err) {
      console.error("❌ Ошибка входа:", err);
      toast.error("Ошибка входа. Проверьте email или пароль.");
    }
    setSubmitting(false);
  };

  const handleRegister = async (values: any, { setSubmitting }: any) => {
    try {
      await api.register({
        email: values.email,
        phone_number: values.phone,
        first_name: values.firstName,
        last_name: values.lastName,
        password_hash: values.password,
      });
      toast.success("Регистрация успешна! Введите код из SMS.");
      setPhoneForVerify(values.phone);
      setView("verify");
    } catch (err) {
      console.error("❌ Ошибка регистрации:", err);
      toast.error("Ошибка регистрации. Такой пользователь уже может существовать.");
    }
    setSubmitting(false);
  };

  const handleVerify = async (values: any, { setSubmitting }: any) => {
    try {
      await api.verifySms(phoneForVerify, values.code);
      toast.success("Телефон успешно подтвержден! Теперь вы можете войти.");
      setView("login");
    } catch (err) {
      console.error("❌ Ошибка верификации:", err);
      toast.error("Неверный код верификации.");
    }
    setSubmitting(false);
  };


  const renderLogin = () => (
    <Formik
      initialValues={{ email: "", password: "" }}
      // TODO: Добавить yup/zod-валидацию
      onSubmit={handleLogin}
    >
      {({ isSubmitting }) => (
        <Form className={styles.form}>
          <h2>Вход в FinFlow</h2>
          <div className={styles.fieldGroup}>
            <label htmlFor="email">Email</label>
            <Field id="email" name="email" placeholder="user@example.com" />
          </div>
          <div className={styles.fieldGroup}>
            <label htmlFor="password">Пароль</label>
            <Field id="password" name="password" type="password" />
          </div>
          <Button type="submit" disabled={isSubmitting} variant="default" size="lg">
            {isSubmitting ? "Вход..." : "Войти"}
          </Button>
        </Form>
      )}
    </Formik>
  );

  const renderRegister = () => (
    <Formik
      initialValues={{ firstName: "", lastName: "", email: "", phone: "", password: "" }}
      onSubmit={handleRegister}
    >
      {({ isSubmitting }) => (
        <Form className={styles.form}>
          <h2>Регистрация</h2>
          <div className={styles.grid}>
            <div className={styles.fieldGroup}>
              <label htmlFor="firstName">Имя</label>
              <Field id="firstName" name="firstName" />
            </div>
            <div className={styles.fieldGroup}>
              <label htmlFor="lastName">Фамилия</label>
              <Field id="lastName" name="lastName" />
            </div>
          </div>
          <div className={styles.fieldGroup}>
            <label htmlFor="email">Email</label>
            <Field id="email" name="email" type="email" />
          </div>
          <div className={styles.fieldGroup}>
            <label htmlFor="phone">Телефон</label>
            <Field id="phone" name="phone" placeholder="+79001234567" />
          </div>
          <div className={styles.fieldGroup}>
            <label htmlFor="password">Пароль</label>
            <Field id="password" name="password" type="password" />
          </div>
          <Button type="submit" disabled={isSubmitting} variant="default" size="lg">
            {isSubmitting ? "Регистрация..." : "Зарегистрироваться"}
          </Button>
        </Form>
      )}
    </Formik>
  );

  const renderVerify = () => (
     <Formik initialValues={{ code: "" }} onSubmit={handleVerify}>
      {({ isSubmitting }) => (
        <Form className={styles.form}>
          <h2>Код из SMS</h2>
          <p className={styles.subtitle}>
            Мы отправили код на номер <strong>{phoneForVerify}</strong>
          </p>
          <div className={styles.fieldGroup}>
            <label htmlFor="code">Код</label>
            <Field id="code" name="code" placeholder="123456" />
          </div>
          <Button type="submit" disabled={isSubmitting} variant="default" size="lg">
            {isSubmitting ? "Проверка..." : "Подтвердить"}
          </Button>
        </Form>
      )}
    </Formik>
  );

  return (
    <div className={styles.authForm}>
      {view === "login" && renderLogin()}
      {view === "register" && renderRegister()}
      {view === "verify" && renderVerify()}

      <div className={styles.footer}>
        {view !== "verify" && (
          <Button
            variant="link"
            className={styles.switchMode}
            onClick={() => setView(view === "login" ? "register" : "login")}
          >
            {view === "login" ? "Нет аккаунта? Регистрация" : "Уже есть аккаунт? Войти"}
          </Button>
        )}
        
        {view === 'login' && (
          <>
            <div className={styles.divider}><span>ИЛИ</span></div>
            <Button variant="outline" size="lg" onClick={api.startBankOAuth}>
              {/* Можно добавить иконку банка */}
              Войти через Банк (OAuth)
            </Button>
          </>
        )}
      </div>
    </div>
  );
};