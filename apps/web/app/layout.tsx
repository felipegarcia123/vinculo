import "./globals.css";
import { AuthGate } from "@/components/AuthGate";

export const metadata = { title: "Vínculo · Fidelización", description: "Conecta con tus clientes. Premia su fidelidad." };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="es"><body><AuthGate>{children}</AuthGate></body></html>;
}
