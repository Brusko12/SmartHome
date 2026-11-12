import { Activity, ArrowRight, Database, House, RefreshCw, ShieldCheck } from 'lucide-react';
import { useHealth } from '../hooks/useHealth';

export function FoundationPage() {
  const { state, refresh } = useHealth();
  const ready = state.kind === 'ready' && state.data.status === 'ok';
  const title = state.kind === 'loading'
    ? 'Проверяем подключение…'
    : ready ? 'Основа системы работает' : 'Требуется внимание';

  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col px-6 py-8 sm:px-10">
      <header className="flex items-center justify-between border-b border-white/10 pb-6">
        <div className="flex items-center gap-3">
          <span className="rounded-2xl bg-violet-500/15 p-3 text-violet-300"><House aria-hidden="true" /></span>
          <span className="text-xl font-semibold tracking-tight">SmartHome</span>
        </div>
        <span className="rounded-full border border-white/10 px-3 py-1 text-xs text-slate-400">Этап 1 · Основа</span>
      </header>

      <section className="my-auto py-16">
        <p className="mb-4 text-sm font-medium uppercase tracking-[0.2em] text-violet-300">Локальный умный дом</p>
        <h1 className="max-w-2xl text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">Всё начинается<br />с надёжной основы.</h1>
        <p className="mt-5 max-w-xl leading-7 text-slate-400">Первый этап SmartHome: подключение интерфейса к серверу и постоянной базе данных. Управление устройствами появится на следующих этапах.</p>

        <section aria-label="Проверка работоспособности" className="mt-10 rounded-3xl border border-white/10 bg-white/[0.03] p-6 sm:p-8">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <Activity className={ready ? 'text-emerald-400' : 'text-slate-400'} aria-hidden="true" />
              <h2 className="text-lg font-medium" aria-live="polite">{title}</h2>
            </div>
            <button type="button" onClick={refresh} disabled={state.kind === 'loading'} className="inline-flex items-center gap-2 rounded-xl bg-violet-500/15 px-4 py-2 text-sm text-violet-200 transition hover:bg-violet-500/25 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-violet-400 disabled:cursor-wait disabled:opacity-50">
              <RefreshCw size={16} aria-hidden="true" /> Проверить снова
            </button>
          </div>
          {state.kind === 'error' && <p role="alert" className="mt-5 text-sm text-rose-300">Не удалось проверить сервер. {state.message}</p>}
          {state.kind === 'ready' && (
            <dl className="mt-6 grid gap-5 border-t border-white/10 pt-6 sm:grid-cols-3">
              <div><dt className="text-sm text-slate-400">Backend</dt><dd className="mt-2">{state.data.status === 'ok' ? 'Доступен' : 'Ошибка проверки'}</dd></div>
              <div><dt className="text-sm text-slate-400">SQLite</dt><dd className="mt-2">{state.data.database === 'ok' ? 'Подключена' : state.data.database === 'migration_required' ? 'Нужна миграция' : 'Недоступна'}</dd></div>
              <div><dt className="text-sm text-slate-400">Версия</dt><dd className="mt-2">{state.data.version}</dd></div>
            </dl>
          )}
        </section>

        <div className="mt-6 flex flex-wrap gap-x-6 gap-y-3 text-sm text-slate-500">
          <span className="inline-flex items-center gap-2"><Database size={16} aria-hidden="true" /> Постоянное хранение</span>
          <span className="inline-flex items-center gap-2"><ShieldCheck size={16} aria-hidden="true" /> Локальный сервер</span>
          <a href="/api/health" className="inline-flex items-center gap-2 text-slate-400 underline-offset-4 hover:underline">Ответ API <ArrowRight size={14} aria-hidden="true" /></a>
        </div>
      </section>

      <footer className="border-t border-white/10 pt-5 text-xs text-slate-500">SmartHome · Разработка по ТЗ v1.0</footer>
    </main>
  );
}
