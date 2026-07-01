import { createBrowserRouter } from "react-router";
import DashboardPage from "./components/DashboardPage";
import AccountLookupPage from "./components/AccountLookupPage";
import AlertQueuePage from "./components/AlertQueuePage";
import AccountDetailPage from "./components/AccountDetailPage";
import ChatPage from "./components/ChatPage";
import ChatActivePage from "./components/ChatActivePage";
import ChatWithModalPage from "./components/ChatWithModalPage";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: DashboardPage,
  },
  {
    path: "/account-lookup",
    Component: AccountLookupPage,
  },
  {
    path: "/alert-queue",
    Component: AlertQueuePage,
  },
  {
    path: "/account/:id",
    Component: AccountDetailPage,
  },
  {
    path: "/chat",
    Component: ChatPage,
  },
  {
    path: "/chat/active",
    Component: ChatActivePage,
  },
  {
    path: "/chat/modal",
    Component: ChatWithModalPage,
  },
]);
