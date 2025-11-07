/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useState } from "react";
import { Formik, Form, Field, ErrorMessage } from "formik";
import styles from "./AuthForm.module.scss";
import { Button } from "../../ui/button";
import { toast } from "sonner";
import * as api from "../../utils/api";
import { setCookie } from "../../utils/cookies";
import { zUserSignIn, zUserSignUp } from "../../utils/zod";
import { toFormikValidationSchema } from 'zod-formik-adapter';
import axios from "axios";

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
      // Обновляем страницу, чтобы хук useAuth сработал заново
      setTimeout(() => {
        window.location.reload();
      }, 500);
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
      password: values.password,
    });
    toast.success("Регистрация успешна! Введите код из SMS.");
    setPhoneForVerify(values.phone);
    setView("verify");
  } catch (err: any) {
    console.error("❌ Ошибка регистрации:", err);
    
    let errorMessage = "Ошибка регистрации. Попробуйте позже.";
    
    if (axios.isAxiosError(err)) {
      if (err.response) {
        errorMessage = err.response.data?.detail || err.response.data?.message || "Ошибка регистрации";
      } else if (err.request) {
        errorMessage = "Ошибка сети. Проверьте подключение к интернету или настройки сервера.";
        
        if (err.message.includes('Network Error')) {
          errorMessage = "Ошибка соединения с сервером. Проверьте, запущен ли бэкенд.";
        }
      } else {
        errorMessage = err.message || "Неизвестная ошибка при настройке запроса";
      }
    }
    
    toast.error(errorMessage);
  } finally {
    setSubmitting(false);
  }
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
      validationSchema={toFormikValidationSchema(zUserSignIn)}
      onSubmit={handleLogin}
    >
      {({ isSubmitting, isValid, dirty, errors, touched }) => (
        <Form className={styles.form}>
          <h2>Вход в FinFlow</h2>
          
          <div className={styles.fieldGroup}>
            <label htmlFor="email">Email</label>
            <Field id="email" name="email" placeholder="user@example.com" />
            <ErrorMessage name="email" component="div" className={styles.error} />
          </div>
          
          <div className={styles.fieldGroup}>
            <label htmlFor="password">Пароль</label>
            <Field id="password" name="password" type="password" />
            <ErrorMessage name="password" component="div" className={styles.error} />
          </div>
          <Button 
            type="submit" 
            disabled={isSubmitting || !isValid || !dirty}
            variant="default" 
            size="lg"
          >
            {isSubmitting ? "Вход..." : "Войти"}
          </Button>
        </Form>
      )}
    </Formik>
  );

  const renderRegister = () => (
    <Formik
      initialValues={{ firstName: "", lastName: "", email: "", phone: "", password: "" }}
      validationSchema={toFormikValidationSchema(zUserSignUp)}
      onSubmit={handleRegister}
    >
      {({ isSubmitting, isValid, dirty, errors, touched }) => (
        <Form className={styles.form}>
          <h2>Регистрация</h2>
          
          <div className={styles.grid}>
            <div className={styles.fieldGroup}>
              <label htmlFor="firstName">Имя</label>
              <Field id="firstName" name="firstName" />
              <ErrorMessage name="firstName" component="div" className={styles.error} />
            </div>
            <div className={styles.fieldGroup}>
              <label htmlFor="lastName">Фамилия</label>
              <Field id="lastName" name="lastName" />
              <ErrorMessage name="lastName" component="div" className={styles.error} />
            </div>
          </div>
          
          <div className={styles.fieldGroup}>
            <label htmlFor="email">Email</label>
            <Field id="email" name="email" type="email" />
            <ErrorMessage name="email" component="div" className={styles.error} />
          </div>
          
          <div className={styles.fieldGroup}>
            <label htmlFor="phone">Телефон</label>
            <Field id="phone" name="phone" placeholder="+79001234567" />
            <ErrorMessage name="phone" component="div" className={styles.error} />
          </div>
          
          <div className={styles.fieldGroup}>
            <label htmlFor="password">Пароль</label>
            <Field id="password" name="password" type="password" />
            <ErrorMessage name="password" component="div" className={styles.error} />
          </div>
          
          <Button 
            type="submit" 
            disabled={isSubmitting || !isValid || !dirty}
            variant="default" 
            size="lg"
          >
            {isSubmitting ? "Регистрация..." : "Зарегистрироваться"}
          </Button>
        </Form>
      )}
    </Formik>
  );

const renderVerify = () => (
  <Formik 
    initialValues={{ code: "" }} 
    onSubmit={handleVerify}
    validate={(values) => {
      const errors: any = {};
      if (!values.code) {
        errors.code = "Обязательное поле";
      } else if (values.code.length < 6) {
        errors.code = "Код должен содержать 6 цифр";
      } else if (!/^\d+$/.test(values.code)) {
        errors.code = "Код должен содержать только цифры";
      }
      return errors;
    }}
  >
    {({ isSubmitting, values, errors, touched, setFieldValue }) => (
      <Form className={styles.form}>
        <h2>Код из SMS</h2>
        <p className={styles.subtitle}>
          Мы отправили код на номер <strong>{phoneForVerify}</strong>
        </p>
        
        <div className={styles.fieldGroup}>
          <label htmlFor="code">Код</label>
          <Field 
            id="code" 
            name="code" 
            placeholder="123456" 
            maxLength={6}
            value={values.code}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
              // Используем setFieldValue вместо прямого изменения DOM
              const value = e.target.value.replace(/\D/g, '');
              setFieldValue('code', value);
            }}
          />
          <ErrorMessage name="code" component="div" className={styles.error} />
        </div>
        
        <Button 
          type="submit" 
          disabled={isSubmitting || values.code.length < 6 || !!errors.code}
          variant="default" 
          size="lg"
        >
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