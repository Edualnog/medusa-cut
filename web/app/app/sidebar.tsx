"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { MedusaLogo } from "../medusa-logo";
import { Icon } from "./icons";

const LINKS = [
  { href: "/app", label: "INÍCIO", icon: "home" },
  { href: "/app/biblioteca", label: "BIBLIOTECA", icon: "library" },
  { href: "/app/apis", label: "CHAVES API", icon: "key" },
  { href: "/app/conta", label: "CONTA", icon: "user" },
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
    <aside className="side2">
      <Link href="/app" className="side2-brand" title="Zorothax">
        <MedusaLogo size={40} />
      </Link>
      <div className="side2-user" title={email}>
        {(email[0] ?? "?").toUpperCase()}
      </div>

      <nav className="side2-nav">
        {LINKS.map((l) => {
          const active = l.href === "/app" ? path === "/app" : path.startsWith(l.href);
          return (
            <Link key={l.href} href={l.href} className={`side2-link${active ? " active" : ""}`}>
              <span className="side2-icon" aria-hidden><Icon name={l.icon} size={22} /></span>
              <span className="side2-label">{l.label}</span>
            </Link>
          );
        })}
      </nav>

      <button className="side2-link side2-logout" onClick={logout}>
        <span className="side2-icon" aria-hidden><Icon name="logout" size={22} /></span>
        <span className="side2-label">SAIR</span>
      </button>
    </aside>
  );
}
