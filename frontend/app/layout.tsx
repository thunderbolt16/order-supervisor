import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import Link from 'next/link';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Order Supervisor',
  description: 'AI-powered order supervision dashboard',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={inter.className}>
        {/* ── Top nav ── */}
        <nav className="sticky top-0 z-50 border-b border-slate-800 bg-[#070e1f]/90 backdrop-blur-md">
          <div className="max-w-screen-2xl mx-auto px-6 h-14 flex items-center gap-6">
            {/* Logo */}
            <Link href="/" className="flex items-center gap-2.5 font-semibold text-white shrink-0">
              <span className="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center text-sm shadow-lg shadow-blue-500/25">
                ⚡
              </span>
              <span className="text-sm tracking-wide">Order Supervisor</span>
            </Link>

            <div className="h-5 w-px bg-slate-800" />

            {/* Nav links */}
            <div className="flex items-center gap-1">
              <Link
                href="/"
                className="px-3 py-1.5 rounded-md text-sm text-slate-400 hover:text-white hover:bg-slate-800/70 transition-all duration-150"
              >
                Dashboard
              </Link>
              <Link
                href="/supervisors"
                className="px-3 py-1.5 rounded-md text-sm text-slate-400 hover:text-white hover:bg-slate-800/70 transition-all duration-150"
              >
                Supervisors
              </Link>
            </div>
          </div>
        </nav>

        <main className="max-w-screen-2xl mx-auto">{children}</main>
      </body>
    </html>
  );
}
