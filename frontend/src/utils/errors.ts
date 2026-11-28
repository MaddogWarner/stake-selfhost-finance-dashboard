import { AxiosError } from 'axios';

export function errorMessage(error: unknown, fallback = 'Something went wrong'): string {
  if (error instanceof AxiosError) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail) && detail.length) {
      return detail.map((item) => (typeof item?.msg === 'string' ? item.msg : String(item))).join('; ');
    }
    return error.message;
  }
  if (error instanceof Error) return error.message;
  return fallback;
}
