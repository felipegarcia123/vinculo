import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Vínculo · Caja de demostración",
  description: "Simula compras ficticias y valida premios de fidelización.",
};

export default function VinculoDemoCashierLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return children;
}
