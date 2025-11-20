import Cookies from 'js-cookie';


export function setCookie(name: string, value: string, days: number) {

  Cookies.set(name, value, { expires: days, path: '/' });
}

export function getCookie(name: string): string | null {
  return Cookies.get(name) || null;
}

export function eraseCookie(name: string) {
  Cookies.remove(name, { path: '/' });
}