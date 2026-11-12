import { Link, Route, Routes } from 'react-router';
import { FoundationPage } from './pages/FoundationPage';

export function App() {
  return (
    <Routes>
      <Route path="/" element={<FoundationPage />} />
      <Route path="*" element={<main className="mx-auto max-w-lg p-10"><h1 className="mb-4 text-2xl">Страница не найдена</h1><Link className="text-violet-300 underline" to="/">На главную</Link></main>} />
    </Routes>
  );
}
