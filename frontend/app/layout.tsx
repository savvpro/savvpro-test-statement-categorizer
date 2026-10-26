import "./globals.css";

export const metadata = {
  title: "Statement Categorizer", // <--- Changed this line
  description: "Sort your transactions automatically.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}