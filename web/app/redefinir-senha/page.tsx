"use client";

// Página única de redefinição de senha. Atende os dois casos do app:
//  - "Esqueci a senha" (deslogado) e "Trocar senha" (logado).
// Em ambos, o app dispara o email de recuperação com redirect_to=esta página.
// O link do email abre aqui já com uma sessão de recuperação; o usuário define a
// nova senha e nós chamamos updateUser. A redefinição é sempre concluída na web.
import { useEffect, useState } from "react";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";
import { MedusaLogo } from "../medusa-logo";

export default function RedefinirSenhaPage() {
  const [hasSession, setHasSession] = useState<boolean | null>(null);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    const supabase = createClient();
    // A sessão de recuperação vem na URL (hash) e é detectada na inicialização.
    supabase.auth.getSession().then(({ data }) => setHasSession(Boolean(data.session)));
    const { data: sub } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session) setHasSession(true);
    });
    return () => sub.subscription.unsubscribe();
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (password.length < 6) {
      setMsg("A senha precisa de ao menos 6 caracteres.");
      return;
    }
    if (password !== confirm) {
      setMsg("As senhas não coincidem.");
      return;
    }
    setLoading(true);
    setMsg(null);
    const supabase = createClient();
    const { error } = await supabase.auth.updateUser({ password });
    setLoading(false);
    if (error) setMsg(error.message);
    else setDone(true);
  }

  return (
    <main className="auth">
      <div className="box auth-card">
        <Link
          href="/"
          className="brand"
          style={{ display: "flex", justifyContent: "center", marginBottom: 18 }}
        >
          <MedusaLogo size={28} /> MEDUSA CLIP
        </Link>
        <h1>NOVA SENHA</h1>

        {done ? (
          <p className="msg">
            Senha alterada! Volte ao app Medusa Clip e entre com a nova senha.
          </p>
        ) : (
          <>
            {hasSession === false && (
              <p className="msg">
                Abra esta página pelo link enviado ao seu e-mail. O link pode ter
                expirado — gere um novo pelo app.
              </p>
            )}
            <form onSubmit={submit}>
              <label className="field">
                <span>NOVA SENHA</span>
                <input
                  type="password"
                  required
                  minLength={6}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                />
              </label>
              <label className="field">
                <span>CONFIRMAR SENHA</span>
                <input
                  type="password"
                  required
                  minLength={6}
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  placeholder="••••••••"
                />
              </label>
              {msg && <p className="msg">{msg}</p>}
              <button className="btn full" type="submit" disabled={loading || hasSession === false}>
                {loading ? "..." : "DEFINIR NOVA SENHA →"}
              </button>
            </form>
          </>
        )}
      </div>
    </main>
  );
}
