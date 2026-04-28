"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    const supabase = createClient();

    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (error) {
      setError(error.message);
      setLoading(false);
      return;
    }

    router.push("/dashboard");
    router.refresh();
  };

  const handleSignUp = async () => {
    setLoading(true);
    setError("");

    const supabase = createClient();

    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo:
          process.env.NEXT_PUBLIC_DEV_SUPABASE_REDIRECT_URL ??
          `${window.location.origin}/auth/callback`,
      },
    });

    if (error) {
      setError(error.message);
      setLoading(false);
      return;
    }

    setError("Verifique seu email para confirmar o cadastro.");
    setLoading(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="w-full max-w-md">
        <div className="bg-card rounded-lg shadow-lg p-8 border border-border">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-primary">CS Controle 360</h1>
            <p className="text-muted-foreground mt-2">
              Sistema de Controle de Homologações
            </p>
          </div>

          <form onSubmit={handleLogin} className="space-y-6">
            <Input
              id="email"
              type="email"
              label="Email"
              placeholder="seu@email.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />

            <Input
              id="password"
              type="password"
              label="Senha"
              placeholder="Sua senha"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />

            {error && (
              <p
                className={`text-sm ${
                  error.includes("Verifique") ? "text-green-600" : "text-danger"
                }`}
              >
                {error}
              </p>
            )}

            <div className="space-y-3">
              <Button
                type="submit"
                className="w-full"
                disabled={loading}
              >
                {loading ? "Entrando..." : "Entrar"}
              </Button>

              <Button
                type="button"
                variant="secondary"
                className="w-full"
                onClick={handleSignUp}
                disabled={loading}
              >
                Criar conta
              </Button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
