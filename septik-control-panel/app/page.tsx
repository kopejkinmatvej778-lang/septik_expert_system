import type { Metadata } from "next";
import DashboardClient from "./DashboardClient";

export const metadata: Metadata = {
  title: "Septik Expert Control",
  description: "Рабочая панель клиентов, КП, договоров, замеров, монтажей и продаж.",
};

export default function Home() {
  return <DashboardClient />;
}
