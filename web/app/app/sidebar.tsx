"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { MedusaLogo } from "../medusa-logo";

const LINKS = [
  { href: "/app", label: "GERAR", icon: "🔗" },
  { href: "/app/biblioteca", label: "BIBLIOTECA", icon: "🎬" },
  { href: "/app/apis", label: "CHAVES API", icon: "🔑" },
  { href: "/app/conta", label: "CONTA", icon: "👤" },
];

export default function Sidebar({ email }: { email: string }) {
  const path = usePathname();
  const router = useRouter();

  async function logout() {
    await createClient().auth.signOut();
    router.push("/login");
    router.refresh();
  }

  return (
    <aside className="sidebar">
      <Link href="/app" className="side-brand">
        <MedusaLogo size={26} /> ZOROTHAX
      </Link>

      <nav className="side-nav">
        {LINKS.map((l) => {
          const active = l.href === "/app" ? path === "/app" : path.startsWith(l.href);
          return (
            <Link key={l.href} href={l.href} className={`side-link${active ? " active" : ""}`}>
              <span aria-hidden>{l.icon}</span> {l.label}
            </Link>
          );
        })}
      </nav>

      <div className="side-foot">
        <div className="side-email">{email}</div>
        <button className="btn side-logout" onClick={logout}>
          SAIR
        </button>
      </div>
    </aside>
  );
}
