import { z } from 'zod';

const passwordSchema = z.string()
    .min(8, 'Пароль должен содержать минимум 8 символов')
    .max(100, 'Пароль не должен превышать 100 символов')
    .regex(/[A-Z]/, 'Пароль должен содержать хотя бы одну заглавную букву')
    .regex(/[a-z]/, 'Пароль должен содержать хотя бы одну строчную букву')
    .regex(/[0-9]/, 'Пароль должен содержать хотя бы одну цифру')
    .default("");


export const zUserSignIn = z.object({
    email: z.email()
        .min(5, 'Email должен содержать минимум 5 символов')
        .max(100, 'Email не должен превышать 100 символов')
        .default(""),

    password: passwordSchema
})


export const zUserSignUp = zUserSignIn.extend({
    firstName: z.string()
        .min(2, 'Имя должно содержать минимум 2 символа')
        .max(50, 'Имя не должно превышать 50 символов')
        .regex(/^[a-zA-Zа-яА-ЯёЁ\s\-]+$/, 'Имя может содержать только буквы, пробелы и дефисы')
        .default(""),

    lastName: z.string()
        .min(2, 'Фамилия должна содержать минимум 2 символа')
        .max(50, 'Фамилия не должна превышать 50 символов')
        .regex(/^[a-zA-Zа-яА-ЯёЁ\s\-]+$/, 'Фамилия может содержать только буквы, пробелы и дефисы')
        .default(""),

    phone: z.string()
        .min(10, 'Телефон должен содержать минимум 10 цифр')
        .max(15, 'Телефон не должен превышать 15 символов')
        .regex(/^\+?[0-9\s\-\(\)]+$/, 'Введите корректный номер телефона')
        .default(""),

});

export type RegisterFormData = z.infer<typeof zUserSignUp>;
export type SignInFormData = z.infer<typeof zUserSignIn>;