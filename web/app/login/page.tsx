"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";
import { MedusaLogo } from "../medusa-logo";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setMsg(null);
    const supabase = createClient();

    if (mode === "login") {
      const { error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) setMsg(error.message);
      else {
        router.push("/app");
        router.refresh();
      }
    } else {
      const { data, error } = await supabase.auth.signUp({ email, password });
      if (error) setMsg(error.message);
      else if (data.session) {
        router.push("/app");
        router.refresh();
      } else {
        setMsg("Conta criada! Confirme o e-mail e depois entre.");
        setMode("login");
      }
    }
    setLoading(false);
  }

  return (
    <main className="auth">
      <div className="box auth-card">
        <Link
          href="/"
          className="brand"
          style={{ display: "flex", justifyContent: "center", marginBottom: 18 }}
        >
          <MedusaLogo size={28} /> ZOROTHAX
        </Link>
        <h1>{mode === "login" ? "ENTRAR" : "CRIAR CONTA"}</h1>
        <form onSubmit={submit}>
          <label className="field">
            <span>E-MAIL</span>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="voce@email.com"
            />
          </label>
          <label className="field">
            <span>SENHA</span>
            <input
              type="password"
              required
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </label>
          {msg && <p className="msg">{msg}</p>}
          <button className="btn full" type="submit" disabled={loading}>
            {loading ? "..." : mode === "login" ? "ENTRAR →" : "CRIAR CONTA →"}
          </button>
        </form>
        <p className="switch">
          {mode === "login" ? "Não tem conta? " : "Já tem conta? "}
          <a onClick={() => { setMode(mode === "login" ? "signup" : "login"); setMsg(null); }}>
            {mode === "login" ? "Criar conta" : "Entrar"}
          </a>
        </p>
      </div>
    </main>
  );
}
