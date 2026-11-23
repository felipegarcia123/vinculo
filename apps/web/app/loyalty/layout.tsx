import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Vínculo · Fidelización",
  description: "Conecta con tus clientes. Premia su fidelidad.",
};

export default function LoyaltyLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return children;
}
