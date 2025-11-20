/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useState } from "react";
import { Formik, Form, Field, ErrorMessage } from "formik";
import styles from "./AuthForm.module.scss";
import { Button } from "../../ui/button";
import { toast } from "sonner";
import * as api from "../../utils/api";
import { initiateBankOAuth } from "../../utils/api";
import { setCookie } from "../../utils/cookies";
import { zUserSignIn, zUserSignUp } from "../../utils/zod";
import { toFormikValidationSchema } from 'zod-formik-adapter';
import { Building2 } from "lucide-react";
import axios from "axios";

type View = "login" | "register" | "verify";

interface AuthFormProps {
  onClose: () => void;
}

export const AuthForm: React.FC<AuthFormProps> = ({ onClose }) => {
  const [view, setView] = useState<View>("login");
  
  const [phoneForVerify, setPhoneForVerify] = useState("");

  const handleLogin = async (values: any, { setSubmitting, setFieldError }: any) => {
    try {
      const { data } = await api.login(values.email, values.password);
      setCookie("access_token", data.access_token, 15 / (24 * 60));
      setCookie("refresh_token", data.refresh_token, 7);
      toast.success("Вход выполнен успешно!", {
        description: "Добро пожаловать!",
        duration: 1500,
      });
      onClose();
      // Обновляем страницу, чтобы хук useAuth сработал заново
      setTimeout(() => {
        window.location.reload();
      }, 500);
    } catch (err: any) {
      console.error("❌ Ошибка входа:", err);
      
      let errorMessage = "Неверный email или пароль";
      let errorDescription = "Проверьте правильность введенных данных";
      
      if (axios.isAxiosError(err)) {
        if (err.response) {
          // Handle 401 Unauthorized specifically
          if (err.response.status === 401) {
            errorMessage = err.response.data?.detail || "Неверный email или пароль";
            errorDescription = "Проверьте правильность email и пароля";
            toast.error(errorMessage, {
              description: errorDescription,
              duration: 1500,
            });
          } else {
            const detail = err.response.data?.detail || err.response.data?.message;
            errorMessage = detail || errorMessage;
            toast.error(errorMessage, {
              description: "Попробуйте еще раз",
              duration: 5000,
            });
          }
          
          // Если есть ошибки валидации, показываем их в полях
          if (err.response.data?.errors && Array.isArray(err.response.data.errors)) {
            err.response.data.errors.forEach((error: any) => {
              const field = error.field || "";
              if (field.includes("email")) {
                setFieldError("email", error.message);
              }
              if (field.includes("password")) {
                setFieldError("password", error.message);
              }
            });
          }
        } else if (err.request) {
          errorMessage = "Ошибка сети";
          errorDescription = "Проверьте подключение к интернету или настройки сервера";
          toast.error(errorMessage, {
            description: errorDescription,
            duration: 1500,
          });
        } else {
          errorMessage = err.message || "Ошибка входа";
          toast.error(errorMessage, {
            description: "Попробуйте еще раз",
            duration: 5000,
          });
        }
      } else {
        toast.error(errorMessage, {
          description: errorDescription,
          duration: 5000,
        });
      }
    }
    setSubmitting(false);
  };

  const handleRegister = async (values: any, { setSubmitting, setFieldError }: any) => {
  try {
    await api.register({
      email: values.email,
      phone_number: values.phone,
      first_name: values.firstName,
      last_name: values.lastName,
      password: values.password,
    });
    
    // После успешной регистрации автоматически логиним пользователя
    toast.success("Регистрация успешна!", {
      description: "Выполняется автоматический вход...",
      duration: 1500,
    });
    
    try {
      const { data } = await api.login(values.email, values.password);
      setCookie("access_token", data.access_token, 15 / (24 * 60));
      setCookie("refresh_token", data.refresh_token, 7);
      toast.success("Добро пожаловать!", {
        description: "Ваш аккаунт успешно создан и активирован",
        duration: 1500,
      });
      onClose();
      // Обновляем страницу, чтобы хук useAuth сработал заново
      setTimeout(() => {
        window.location.reload();
      }, 500);
    } catch (loginErr: any) {
      console.error("❌ Ошибка автоматического входа после регистрации:", loginErr);
      toast.error("Регистрация успешна, но не удалось войти", {
        description: "Пожалуйста, войдите вручную",
        duration: 1500,
      });
      setView("login");
    }
  } catch (err: any) {
    console.error("❌ Ошибка регистрации:", err);
    
    let errorMessage = "Ошибка регистрации";
    let errorDescription = "Попробуйте позже";
    let hasValidationErrors = false;
    
    if (axios.isAxiosError(err)) {
      if (err.response) {
        const responseData = err.response.data;
        
        // Handle specific error codes
        if (err.response.status === 409) {
          errorMessage = "Пользователь уже существует";
          errorDescription = responseData?.detail || "Email или номер телефона уже зарегистрирован";
        } else if (err.response.status === 422) {
          errorMessage = "Ошибка валидации данных";
          errorDescription = "Проверьте правильность заполнения полей";
        } else {
          errorMessage = responseData?.detail || responseData?.message || "Ошибка регистрации";
          errorDescription = "Попробуйте еще раз";
        }
        
        // Если есть ошибки валидации, показываем их в полях
        if (responseData?.errors && Array.isArray(responseData.errors)) {
          hasValidationErrors = true;
          responseData.errors.forEach((error: any) => {
            const field = error.field || "";
            if (field.includes("email")) {
              setFieldError("email", error.message);
            }
            if (field.includes("phone") || field.includes("phone_number")) {
              setFieldError("phone", error.message);
            }
            if (field.includes("first_name") || field.includes("firstName")) {
              setFieldError("firstName", error.message);
            }
            if (field.includes("last_name") || field.includes("lastName")) {
              setFieldError("lastName", error.message);
            }
            if (field.includes("password")) {
              setFieldError("password", error.message);
            }
          });
        }
        
        // Показываем общее сообщение об ошибке
        if (hasValidationErrors && responseData.errors.length > 0) {
          toast.error("Проверьте правильность заполнения полей", {
            description: "Исправьте ошибки в форме",
            duration: 1500,
          });
        } else {
          toast.error(errorMessage, {
            description: errorDescription,
            duration: 1500,
          });
        }
      } else if (err.request) {
        errorMessage = "Ошибка сети";
        errorDescription = "Проверьте подключение к интернету или настройки сервера";
        toast.error(errorMessage, {
          description: errorDescription,
          duration: 1500,
        });

        if (err.message.includes('Network Error')) {
          toast.error("Ошибка соединения с сервером", {
            description: "Проверьте, запущен ли бэкенд",
            duration: 1500,
          });
        }
      } else {
        errorMessage = err.message || "Неизвестная ошибка";
        toast.error(errorMessage, {
          description: "Попробуйте еще раз",
          duration: 1500,
        });
      }
    } else {
      toast.error(errorMessage, {
        description: errorDescription,
        duration: 1500,
      });
    }
  } finally {
    setSubmitting(false);
  }
};

  const handleVerify = async (values: any, { setSubmitting }: any) => {
    try {
      await api.verifySms(phoneForVerify, values.code);
      toast.success("Телефон успешно подтвержден!", {
        description: "Теперь вы можете войти",
        duration: 1500,
      });
      setView("login");
    } catch (err: any) {
      console.error("❌ Ошибка верификации:", err);
      const errorMessage = err.response?.data?.detail || "Неверный код верификации";
      toast.error("Ошибка верификации", {
        description: errorMessage,
        duration: 1500,
      });
    }
    setSubmitting(false);
  };


  const handleBankOAuth = (bankCode: string) => {
    toast.info("Перенаправление на банк для авторизации...", {
      description: "Вы будете перенаправлены на страницу банка",
      duration: 1500,
    });
    initiateBankOAuth(bankCode);
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
            <Field 
              id="email" 
              name="email" 
              placeholder="user@example.com"
              className={errors.email && touched.email ? styles.fieldError : ""}
            />
            <ErrorMessage name="email" component="div" className={styles.error} />
          </div>
          
          <div className={styles.fieldGroup}>
            <label htmlFor="password">Пароль</label>
            <Field 
              id="password" 
              name="password" 
              type="password"
              className={errors.password && touched.password ? styles.fieldError : ""}
            />
            <ErrorMessage name="password" component="div" className={styles.error} />
          </div>
          
          <Button 
            type="submit" 
            disabled={isSubmitting || !isValid || !dirty}
            variant="default" 
            size="lg"
            className={styles.loginButton}
          >
            {isSubmitting ? "Вход..." : "Войти"}
          </Button>

          <div className={styles.divider}></div>

          <div className={styles.oauthSection}>
            <p className={styles.oauthTitle}>Войти через</p>
            <div className={styles.oauthButtons}>
              <Button
                type="button"
                variant="outline"
                size="lg"
                onClick={() => handleBankOAuth("vbank")}
                className={styles.oauthButton}
              >
                <Building2 size={20} />
                Virtual Bank
              </Button>
              <Button
                type="button"
                variant="outline"
                size="lg"
                onClick={() => handleBankOAuth("abank")}
                className={styles.oauthButton}
              >
                <Building2 size={20} />
                Awesome Bank
              </Button>
              <Button
                type="button"
                variant="outline"
                size="lg"
                onClick={() => handleBankOAuth("sbank")}
                className={styles.oauthButton}
              >
                <Building2 size={20} />
                Smart Bank
              </Button>
            </div>
          </div>
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
              <Field 
                id="firstName" 
                name="firstName"
                className={errors.firstName && touched.firstName ? styles.fieldError : ""}
              />
              <ErrorMessage name="firstName" component="div" className={styles.error} />
            </div>
            <div className={styles.fieldGroup}>
              <label htmlFor="lastName">Фамилия</label>
              <Field 
                id="lastName" 
                name="lastName"
                className={errors.lastName && touched.lastName ? styles.fieldError : ""}
              />
              <ErrorMessage name="lastName" component="div" className={styles.error} />
            </div>
          </div>
          
          <div className={styles.fieldGroup}>
            <label htmlFor="email">Email</label>
            <Field 
              id="email" 
              name="email" 
              type="email"
              className={errors.email && touched.email ? styles.fieldError : ""}
            />
            <ErrorMessage name="email" component="div" className={styles.error} />
          </div>
          
          <div className={styles.fieldGroup}>
            <label htmlFor="phone">Телефон</label>
            <Field 
              id="phone" 
              name="phone" 
              placeholder="+79001234567"
              className={errors.phone && touched.phone ? styles.fieldError : ""}
            />
            <ErrorMessage name="phone" component="div" className={styles.error} />
          </div>
          
          <div className={styles.fieldGroup}>
            <label htmlFor="password">Пароль</label>
            <Field 
              id="password" 
              name="password" 
              type="password"
              className={errors.password && touched.password ? styles.fieldError : ""}
            />
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
          Мы отправили код на номер <strong>{phoneForVerify || ""}</strong>
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
      </div>
    </div>
  );
};