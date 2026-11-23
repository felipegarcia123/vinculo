import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Vínculo · Iniciar sesión",
  description: "Conecta con tus clientes. Premia su fidelidad.",
};

export default function LoginLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return children;
}
