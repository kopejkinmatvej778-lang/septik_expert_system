import type { Metadata } from "next";
import DashboardClient from "./DashboardClient";
import { requireChatGPTUser } from "./chatgpt-auth";

export const metadata: Metadata = {
  title: "Septik Expert Control",
  description: "Рабочая панель клиентов, КП, договоров, замеров, монтажей и продаж.",
};

export default async function Home() {
  const user = await requireChatGPTUser("/");
  return <DashboardClient userName={user.displayName} />;
}
