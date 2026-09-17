"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  CheckSquare,
  FileText,
  Settings,
  ListTodo,
  Package,
  BookOpen,
  LogOut,
} from "lucide-react";

const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "Homologações", href: "/dashboard/homologacoes", icon: CheckSquare },
  { name: "Customizações", href: "/dashboard/customizacoes", icon: FileText },
  { name: "Atividades", href: "/dashboard/atividades", icon: ListTodo },
  { name: "Releases", href: "/dashboard/releases", icon: Package },
  { name: "Playbooks", href: "/dashboard/playbooks", icon: BookOpen },
  { name: "Admin", href: "/dashboard/admin", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed inset-y-0 left-0 z-50 w-64 bg-primary text-white flex flex-col">
      <div className="flex h-16 items-center px-6 border-b border-primary-light">
        <h1 className="text-xl font-bold">CS Controle 360</h1>
      </div>

      <nav className="flex-1 p-4 space-y-1">
        {navigation.map((item) => {
          const isActive =
            pathname === item.href ||
            (item.href !== "/dashboard" && pathname?.startsWith(item.href));

          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary-light text-white"
                  : "text-white/80 hover:bg-primary-light/50 hover:text-white"
              )}
            >
              <item.icon className="h-5 w-5" />
              {item.name}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-primary-light">
        <form action="/auth/logout" method="POST">
          <button
            type="submit"
            className="flex w-full items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium text-white/80 hover:bg-primary-light/50 hover:text-white transition-colors"
          >
            <LogOut className="h-5 w-5" />
            Sair
          </button>
        </form>
      </div>
    </aside>
  );
}
