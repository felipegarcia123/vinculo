import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Vínculo · Panel de fidelización",
  description: "Conecta con tus clientes. Premia su fidelidad.",
};

export default function LoyaltyOwnerLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return children;
}
