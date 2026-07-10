# Weave Agent UI — Design Skill Reference

This document captures the design system conventions, component patterns, and Tailwind/MUI usage derived from production components. Use it as the authoritative reference when building new UI.

---

## Design Tokens

### Color Palette

| Token | Value | Usage |
|---|---|---|
| Gold primary | `#E2CD78` | Avatar bg, badge bg, accents |
| Gold border | `#CBB355` | Badge borders |
| Gold text | `#846C00` | Subtitle / role text |
| Gold gradient start | `#E7D793` | Dropdown backgrounds |
| Black overlay | `rgba(0,0,0,0.08)` | Hover backgrounds |
| Glass bg | `rgba(255,255,255,0.34)` | Header / panel backgrounds |
| White border | `rgba(255,255,255,0.9)` | Dropdown/card borders |

### Typography

- **Font family**: `Inter, sans-serif`
- **Labels / nav items**: `text-[13px] font-semibold uppercase leading-[1.1]`
- **Dropdown labels**: `text-[12.5px] font-semibold uppercase`
- **Small badges**: `text-[9.5px] font-bold uppercase tracking-[0.24px]`
- **User name**: `text-[14px] leading-[20px] font-semibold uppercase`
- **Body / descriptions**: `text-[11px] leading-[1.8]`
- **Tooltips**: `fontSize: 12, fontWeight: 500`

---

## Layout Conventions

### Header Shell
```
h-[60px]  px-[38px]  py-[11px]
sticky top-0 left-0 z-30
flex items-center justify-between
shadow-[0_1px_5px_0_rgba(0,0,0,0.10)]
backdrop-blur-[12px]
border-b-[1.5px] border-b-white border-solid
bg-[rgba(255,255,255,0.34)]
```

### Section Dividers
```tsx
<div className="h-6 w-px bg-black/15" />
```

### Icon Buttons (header actions)
```
flex h-8 w-8 cursor-pointer items-center justify-center
rounded-[8px] transition-colors hover:bg-black/[0.08]
```

---

## Dropdown / Menu Panel

### Container
```tsx
className="absolute right-0 top-full mt-2 z-20
  w-[435px] max-w-[calc(100vw-20px)]
  overflow-hidden rounded-[14px]
  border border-[rgba(255,255,255,0.9)]
  shadow-[0px_6px_15px_0px_rgba(0,0,0,0.22)]"
style={{
  backgroundImage:
    "linear-gradient(90deg, rgba(255,255,255,0.18) 0%, rgba(255,255,255,0.18) 100%), linear-gradient(135deg, #E7D793 0%, #ECE9DC 58%, #F2F2F2 100%)",
}}
```

### Profile Dropdown (narrower variant)
```tsx
// w-[316px], different gradient angle
style={{
  backgroundImage:
    "linear-gradient(90deg, rgba(255,255,255,0.2) 0%, rgba(255,255,255,0.2) 100%), linear-gradient(330.45deg, #EDEDED 52.87%, #E3D693 97.2%)",
}}
```

### Menu Row Item (`MenuOption`)
```tsx
<button
  type="button"
  role="menuitem"
  onClick={onClick}
  className="group mb-1.5 flex h-9 w-full cursor-pointer items-center justify-between rounded-none px-3.5 transition-colors"
>
  <div className="flex h-full items-center gap-2.5">
    <img src={icon} alt="" className="h-4.5 w-4.5 shrink-0" aria-hidden="true" />
    <span className="text-[12.5px] leading-none font-semibold uppercase text-black">
      {label}
    </span>
  </div>
  <img
    src={arrowIcon}
    alt=""
    className="h-3 w-3.5 shrink-0 transition-transform duration-200 group-hover:translate-x-0.5"
    aria-hidden="true"
  />
</button>
```

---

## MUI Tooltip — Standard Config

Always use `headerTooltipSlotProps` for consistent tooltip styling:

```tsx
const headerTooltipSlotProps = {
  popper: {
    modifiers: [{ name: "offset", options: { offset: [0, -6] } }],
  },
  tooltip: {
    style: {
      fontSize: 12,
      fontFamily: "Inter, sans-serif",
      fontWeight: 500,
      background: "#333333",
      color: "#ffffff",
      boxShadow: "0 0 15px 0 rgba(0, 0, 0, 0.25)",
      borderRadius: "0 8px 8px 8px",
      padding: "6px 12px",
    },
  },
};

<Tooltip
  title="Label"
  placement="bottom"
  enterDelay={150}
  slotProps={headerTooltipSlotProps}
>
  {/* trigger */}
</Tooltip>
```

---

## Animation Patterns (Framer Motion)

### `SmartAnimateIconContainer` — Reusable Icon Hover Shell

Wraps any icon to add a subtle scale + brightness hover effect with an animated background pill.

```tsx
const SmartAnimateIconContainer = ({
  active,
  blinkOnActive = false,
  children,
}: {
  active: boolean;
  blinkOnActive?: boolean;
  children: ReactNode;
}) => {
  const frameSizeClass = "h-8 w-8";

  return (
    <span className={`relative inline-flex items-center justify-center overflow-visible ${frameSizeClass}`}>
      <motion.span
        aria-hidden="true"
        className="pointer-events-none absolute h-8 w-8 rounded-[10px] bg-black/[0.05]"
        animate={{
          opacity: active ? 1 : 0,
          scale: active ? 1.03 : 0.95,
        }}
        transition={{ duration: 0.3, ease: "easeInOut" }}
      />
      <motion.span
        className="relative z-10 inline-flex items-center justify-center"
        animate={{
          scale: active ? 1.04 : 1,
          filter: active
            ? "brightness(0) saturate(100%) contrast(1.12)"
            : "brightness(0) saturate(100%) contrast(1)",
          opacity: blinkOnActive && active ? [1, 0.32, 1] : 1,
        }}
        transition={{
          duration: 0.3,
          ease: "easeInOut",
          times: blinkOnActive && active ? [0, 0.45, 1] : undefined,
        }}
      >
        {children}
      </motion.span>
    </span>
  );
};
```

Usage:
```tsx
const [active, setActive] = useState(false);
<button
  onMouseEnter={() => setActive(true)}
  onMouseLeave={() => setActive(false)}
  onFocus={() => setActive(true)}
  onBlur={() => setActive(false)}
>
  <SmartAnimateIconContainer active={active}>
    <img src={icon} alt="Label" className="h-4.5 w-4.5" />
  </SmartAnimateIconContainer>
</button>
```

### Expand / Collapse (AnimatePresence)
```tsx
// Entry: slide up from below + fade in
initial={{ y: 60, opacity: 0 }}
animate={{ y: 0, opacity: 1 }}
exit={{ y: -40, opacity: 0 }}
transition={{ duration: 0.38, ease: [0.22, 1, 0.36, 1] }}

// Entry: slide from right + fade in (for inline arrow buttons)
initial={{ x: 8, opacity: 0 }}
animate={{ x: 0, opacity: 1 }}
exit={{ x: 8, opacity: 0 }}
transition={{ duration: 0.3, ease: "easeInOut" }}
```

### Profile Avatar Hover (parallax shift)
```tsx
<motion.span
  animate={{
    x: active ? -0.9 : 0,
    y: active ? 0.9 : 0,
  }}
  transition={{ duration: 0.3, ease: "easeInOut" }}
>
```

---

## Avatar

```tsx
// With image
<img
  src={profileImage}
  alt={fullName}
  className="h-9 w-9 rounded-full object-cover"
/>

// Fallback initials
<span className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-[#E2CD78] text-[11px] font-bold text-black">
  {avatarInitials}
</span>
```

Initials derivation:
```ts
const avatarInitials = useMemo(() => {
  const source = fullName || username || email || "User";
  const words = source.split(/\s+/).filter(Boolean);
  if (!words.length) return "U";
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return `${words[0][0] || ""}${words[1][0] || ""}`.toUpperCase();
}, [fullName, username, email]);
```

---

## Outside-Click Handler Pattern

```tsx
const ref = useRef<HTMLDivElement | null>(null);

useEffect(() => {
  const handleOutsideClick = (event: MouseEvent) => {
    if (!ref.current?.contains(event.target as Node)) {
      setOpen(false);
    }
  };
  document.addEventListener("mousedown", handleOutsideClick);
  return () => document.removeEventListener("mousedown", handleOutsideClick);
}, []);
```

---

## Badge (Agent Count)

```tsx
<span className="inline-flex items-center gap-1 rounded-[7px] border border-[#CBB355] bg-[#E2CD78] px-2 py-[3px] text-[9.5px] font-bold uppercase tracking-[0.24px] text-black">
  {count} agents
</span>
```

---

## Image Mask (gradient fade)

Used for decorative panel images to fade in from left:
```tsx
style={{
  backgroundImage: `url(${image})`,
  WebkitMaskImage: "linear-gradient(to right, transparent 0%, black 30%)",
  maskImage: "linear-gradient(to right, transparent 0%, black 30%)",
}}
```

---

---

## AppLayout — Page Shell

### Structure Overview

```
<div h-screen overflow-hidden flex>
  ├── Mobile sidebar overlay (fixed, z-40, lg:hidden)
  └── <Box id="scroll-container" flex-col flex-1 bg=landingBg>
        ├── <Header />
        ├── <Breadcrumb />
        ├── <main id="main-content" flex-1>
        │     <Outlet />
        ├── [conditional footer — dashboard only]
        └── [RT logo watermark — non-dashboard routes]
```

### Scroll Container
```tsx
<Box
  id="scroll-container"
  className={`flex flex-col flex-1 min-w-0 ${
    isAgentsRoute
      ? "overflow-y-auto overflow-x-hidden xl:overflow-hidden"
      : "overflow-y-auto"
  }`}
  sx={{
    background: `url(${landingBg})`,
    backgroundSize: "cover",
    backgroundRepeat: "no-repeat",
  }}
>
```
- Uses MUI `Box` for the `sx` background image — **do not** use a `<div>` with inline style here.
- The `id="scroll-container"` is referenced by virtual scroll / infinite list hooks.
- Agents route disables horizontal scroll and locks overflow on `xl+` screens.

### Mobile Sidebar Overlay
```tsx
{mobileSidebarOpen && (
  <div className="lg:hidden fixed inset-0 z-40 flex">
    <div
      className="absolute inset-0 bg-black/50"
      aria-hidden="true"
      onClick={() => setMobileSidebarOpen(false)}
    />
    <div className="relative z-50">
      <Sidebar collapsed={false} onToggle={() => setMobileSidebarOpen(false)} />
    </div>
  </div>
)}
```
- Backdrop is `bg-black/50`, `aria-hidden`.
- Sidebar sits at `z-50` above the backdrop.
- Dismissed by clicking the backdrop or the sidebar toggle.

### Dashboard Footer (conditional)
```tsx
{showDashboardFooter && (
  <footer className="px-12 h-13 flex items-end justify-between bg-transparent">
    <p className="text-black font-['Inter',sans-serif] text-[10.5px] font-normal leading-normal">
      © 2026 All rights reserved
    </p>
    <img src={RTlogo} alt="Powered by RandomTrees" className="h-11 w-auto" />
    <div className="text-black font-['Inter',sans-serif] text-[10.5px] font-normal leading-normal flex items-center gap-3">
      <a href="#" className="hover:underline">Terms of Service</a>
      <span className="text-[rgba(0,0,0,0.3)]">|</span>
      <a href="#" className="hover:underline">Privacy Policy</a>
    </div>
  </footer>
)}
```

### RT Logo Watermark (non-dashboard)
```tsx
{!showDashboardFooter && (
  <img
    src={RTlogo}
    alt=""
    aria-hidden="true"
    className="fixed bottom-0 right-1 z-50 pointer-events-none"
  />
)}
```

### Route-based Conditional Logic
```ts
const showDashboardFooter = location.pathname === "/dashboard";
const isAgentsRoute = matchPath('/dashboard/:categoryId/agents', location.pathname);
```

### Template: Full AppLayout Component
```tsx
import { useState } from "react";
import { matchPath, Outlet, useLocation } from "react-router-dom";
import RTlogo from "@/assets/RT-logo.svg";
import { Header } from "@/components/layout/header";
import { Sidebar } from "@/components/layout/sidebar";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Box } from "@mui/material";
import landingBg from "@/assets/module/market-place/Landing.svg";

export const AppLayout = () => {
	const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
	const location = useLocation();
	const showDashboardFooter = location.pathname === "/dashboard";
	const isAgentsRoute = matchPath('/dashboard/:categoryId/agents', location.pathname);

	return (
		<div className="flex h-screen overflow-hidden">
			{mobileSidebarOpen && (
				<div className="lg:hidden fixed inset-0 z-40 flex">
					<div
						className="absolute inset-0 bg-black/50"
						aria-hidden="true"
						onClick={() => setMobileSidebarOpen(false)}
					/>
					<div className="relative z-50">
						<Sidebar
							collapsed={false}
							onToggle={() => setMobileSidebarOpen(false)}
						/>
					</div>
				</div>
			)}

			<Box
				id="scroll-container"
				className={`flex flex-col flex-1 min-w-0 ${isAgentsRoute ? "overflow-y-auto overflow-x-hidden xl:overflow-hidden" : "overflow-y-auto"}`}
				sx={{
					background: `url(${landingBg})`,
					backgroundSize: "cover",
					backgroundRepeat: "no-repeat",
				}}
			>
				<Header
					showMenuButton
					onMenuToggle={() => setMobileSidebarOpen((o) => !o)}
				/>
				<Breadcrumb />
				<main id="main-content" className="flex-1">
					<Outlet />
				</main>
				{showDashboardFooter && (
					<footer className="px-12 h-13 flex items-end justify-between bg-transparent">
						<div className="h-full flex items-center">
							<p className="text-black font-['Inter',sans-serif] text-[10.5px] not-italic font-normal leading-normal">
								© 2026 All rights reserved
							</p>
						</div>
						<div className="h-11 flex items-center">
							<img src={RTlogo} alt="Powered by RandomTrees" className="h-11 w-auto" />
						</div>
						<div className="h-full flex items-center">
							<div className="text-black font-['Inter',sans-serif] text-[10.5px] not-italic font-normal leading-normal flex items-center gap-3">
								<a href="#" className="hover:underline">Terms of Service</a>
								<span className="text-[rgba(0,0,0,0.3)]">|</span>
								<a href="#" className="hover:underline">Privacy Policy</a>
							</div>
						</div>
					</footer>
				)}
			</Box>
			{!showDashboardFooter && (
				<img
					src={RTlogo}
					alt=""
					aria-hidden="true"
					className="fixed bottom-0 right-1 z-50 pointer-events-none"
				/>
			)}
		</div>
	);
};
```

---

## Sidebar

### Design Language
- Dark background: `bg-sidebar-bg` (`--color-sidebar-bg: #0f0e22` in `index.css`)
- Collapse widths: `w-18` (collapsed) / `w-65` (expanded)
- Transition: `transition-all duration-300 ease-in-out`
- Section dividers: `border-white/10`
- Icon size: `fontSize: 18` (MUI)

### Logo Area
```tsx
<div className={cn(
  "flex items-center h-16 shrink-0 border-b border-white/10",
  collapsed ? "justify-center px-0" : "px-5",
)}>
  {/* Collapsed: icon only */}
  <div className="flex items-center justify-center w-9 h-9 bg-orange-500 rounded-lg">
    <span className="font-bold text-sm text-white">W</span>
  </div>

  {/* Expanded: icon + text */}
  <div className="flex items-center gap-2.5">
    <div className="flex items-center justify-center w-9 h-9 bg-orange-500 rounded-lg shrink-0">
      <span className="font-bold text-sm text-white">W</span>
    </div>
    <div>
      <p className="font-bold text-sm leading-none text-white">Weave Agent</p>
      <p className="text-xs text-white/50 mt-0.5">AI Marketplace</p>
    </div>
  </div>
</div>
```

### Nav Items Area
```tsx
<div className="flex-1 overflow-y-auto py-4 flex flex-col gap-1 px-3">
  {NAV_ITEMS.map((item) => (
    <NavItem key={item.href} item={item} collapsed={collapsed} />
  ))}
</div>
```

### `NavItem` — Active / Inactive States
```tsx
const NavItem = ({ item, collapsed }: { item: SidebarItem; collapsed: boolean }) => {
  const { pathname } = useLocation();
  const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);

  return (
    <Link
      to={item.href}
      aria-current={isActive ? "page" : undefined}
      title={collapsed ? item.label : undefined}
      className={cn(
        "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400",
        isActive
          ? "bg-orange-500/15 text-orange-400"
          : "text-white/60 hover:text-white hover:bg-white/8",
        collapsed && "justify-center px-0 w-10 h-10 mx-auto",
      )}
    >
      <span className={cn("shrink-0", isActive && "text-orange-400")}>
        {item.icon}
      </span>
      {!collapsed && <span className="truncate">{item.label}</span>}
    </Link>
  );
};
```

Active state tokens:
| State | Background | Text |
|---|---|---|
| Active | `bg-orange-500/15` | `text-orange-400` |
| Hover | `hover:bg-white/8` | `hover:text-white` |
| Default | — | `text-white/60` |

### Collapse Toggle Button
```tsx
<button
  type="button"
  onClick={onToggle}
  aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
  className="flex items-center justify-center w-8 h-8 rounded-lg text-white/50 hover:text-white hover:bg-white/10 transition-colors"
>
  {collapsed
    ? <ChevronRightRoundedIcon sx={{ fontSize: 16 }} />
    : <ChevronLeftRoundedIcon sx={{ fontSize: 16 }} />
  }
</button>
```

### Nav Item Data Shape
```ts
interface SidebarItem {
  label: string;
  href: string;
  icon: React.ReactNode;  // MUI icon at fontSize: 18
}

const NAV_ITEMS: SidebarItem[] = [
  { label: "Dashboard", href: "/dashboard", icon: <DashboardRoundedIcon sx={{ fontSize: 18 }} /> },
  { label: "Agents",    href: "/agents",    icon: <SmartToyRoundedIcon sx={{ fontSize: 18 }} /> },
  { label: "AI Metrics",href: "/ai-metrics",icon: <BarChartRoundedIcon sx={{ fontSize: 18 }} /> },
];
```

### Template: Full Sidebar Component
```tsx
import BarChartRoundedIcon from "@mui/icons-material/BarChartRounded";
import ChevronLeftRoundedIcon from "@mui/icons-material/ChevronLeftRounded";
import ChevronRightRoundedIcon from "@mui/icons-material/ChevronRightRounded";
import DashboardRoundedIcon from "@mui/icons-material/DashboardRounded";
import SmartToyRoundedIcon from "@mui/icons-material/SmartToyRounded";
import { Link, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";

export interface SidebarItem {
	label: string;
	href: string;
	icon: React.ReactNode;
}

const NAV_ITEMS: SidebarItem[] = [
	{ label: "Dashboard", href: "/dashboard", icon: <DashboardRoundedIcon sx={{ fontSize: 18 }} /> },
	{ label: "Agents", href: "/agents", icon: <SmartToyRoundedIcon sx={{ fontSize: 18 }} /> },
	{ label: "AI Metrics", href: "/ai-metrics", icon: <BarChartRoundedIcon sx={{ fontSize: 18 }} /> },
];

const BOTTOM_ITEMS: SidebarItem[] = [];

interface SidebarProps {
	collapsed: boolean;
	onToggle: () => void;
}

export const Sidebar = ({ collapsed, onToggle }: SidebarProps) => {
	return (
		<nav
			aria-label="Main navigation"
			className={cn(
				"flex flex-col h-screen bg-sidebar-bg text-white",
				"transition-all duration-300 ease-in-out",
				collapsed ? "w-18" : "w-65",
			)}
		>
			<div
				className={cn(
					"flex items-center h-16 shrink-0 border-b border-white/10",
					collapsed ? "justify-center px-0" : "px-5",
				)}
			>
				{collapsed ? (
					<div className="flex items-center justify-center w-9 h-9 bg-orange-500 rounded-lg">
						<span className="font-bold text-sm text-white">W</span>
					</div>
				) : (
					<div className="flex items-center gap-2.5">
						<div className="flex items-center justify-center w-9 h-9 bg-orange-500 rounded-lg shrink-0">
							<span className="font-bold text-sm text-white">W</span>
						</div>
						<div>
							<p className="font-bold text-sm leading-none text-white">Weave Agent</p>
							<p className="text-xs text-white/50 mt-0.5">AI Marketplace</p>
						</div>
					</div>
				)}
			</div>

			<div className="flex-1 overflow-y-auto py-4 flex flex-col gap-1 px-3">
				{NAV_ITEMS.map((item) => (
					<NavItem key={item.href} item={item} collapsed={collapsed} />
				))}
			</div>

			<div className="border-t border-white/10 py-4 flex flex-col gap-1 px-3">
				{BOTTOM_ITEMS.map((item) => (
					<NavItem key={item.href} item={item} collapsed={collapsed} />
				))}
			</div>

			<div className={cn("pb-4 flex", collapsed ? "justify-center" : "px-3")}>
				<button
					type="button"
					onClick={onToggle}
					aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
					className="flex items-center justify-center w-8 h-8 rounded-lg text-white/50 hover:text-white hover:bg-white/10 transition-colors"
				>
					{collapsed
						? <ChevronRightRoundedIcon sx={{ fontSize: 16 }} />
						: <ChevronLeftRoundedIcon sx={{ fontSize: 16 }} />
					}
				</button>
			</div>
		</nav>
	);
};

const NavItem = ({ item, collapsed }: { item: SidebarItem; collapsed: boolean }) => {
	const { pathname } = useLocation();
	const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);

	return (
		<Link
			to={item.href}
			aria-label={collapsed ? item.label : undefined}
			aria-current={isActive ? "page" : undefined}
			title={collapsed ? item.label : undefined}
			className={cn(
				"flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all",
				"focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400",
				isActive
					? "bg-orange-500/15 text-orange-400"
					: "text-white/60 hover:text-white hover:bg-white/8",
				collapsed && "justify-center px-0 w-10 h-10 mx-auto",
			)}
		>
			<span className={cn("shrink-0", isActive && "text-orange-400")}>
				{item.icon}
			</span>
			{!collapsed && <span className="truncate">{item.label}</span>}
		</Link>
	);
};
```

---

## Template: Full Header Component

```tsx
import MenuRoundedIcon from "@mui/icons-material/MenuRounded";
import { agentsResetPending } from "@/utils/agents-nav-state";
import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import headerWeave from "@/assets/headerWeave.svg";
import question from "@/assets/question.svg";
import settingsIcon from "@/assets/settings.svg";
import logoutIcon from "@/assets/logout.svg";
import nextArrowIcon from "@/assets/next-arrow.svg";
import waveAgentLetter from "@/assets/wave-agent-letter.png";
import dotCircle from "@/assets/dot-cirlce.svg";
import dotSquare from "@/assets/dot-square.svg";
import cloudIcon from "@/assets/cloud.svg";
import codeIcon from "@/assets/code.svg";
import connectCircuitIcon from "@/assets/connect-circuit.svg";
import layersIcon from "@/assets/Layers.svg";
import img2 from "@/assets/img2.png";
import img3 from "@/assets/img3.png";
import img4 from "@/assets/img4.png";
import img1 from "@/assets/img1.svg";
import { useLogoutMutation } from "@/hooks/useAuthMutations";
import { useAuthStore } from "@/store/auth";
import { useQuery } from "@tanstack/react-query";
import { getMarketplaceCategoriesQueryOptions } from "@/hooks/useDashboard";
import { useRouteMeta } from "@/types/router";
import { Button, Tooltip } from "@mui/material";
import ChevronLeft from '@mui/icons-material/ChevronLeft';

interface HeaderProps {
	onMenuToggle?: () => void;
	showMenuButton?: boolean;
}

export const Header = ({ onMenuToggle, showMenuButton }: HeaderProps) => {
	const { user } = useAuthStore();
	const params = useParams();
	const logoutMutation = useLogoutMutation();
	const navigate = useNavigate();
	const [dropdownOpen, setDropdownOpen] = useState(false);
	const [browseMenuOpen, setBrowseMenuOpen] = useState(false);
	const [activeBrowseIndex, setActiveBrowseIndex] = useState<number | null>(null);
	const [helpActive, setHelpActive] = useState(false);
	const [profileHover, setProfileHover] = useState(false);
	const [profileTooltipOpen, setProfileTooltipOpen] = useState(false);
	const browseMenuRef = useRef<HTMLDivElement | null>(null);
	const profileMenuRef = useRef<HTMLDivElement | null>(null);
	const headerTooltipSlotProps = {
		popper: {
			modifiers: [
				{
					name: "offset",
					options: {
						offset: [0, -6],
					},
				},
			],
		},
		tooltip: {
			style: {
				fontSize: 12,
				fontFamily: "Inter, sans-serif",
				fontWeight: 500,
				background: "#333333",
				color: "#ffffff",
				boxShadow: "0 0 15px 0 rgba(0, 0, 0, 0.25)",
				borderRadius: "0 8px 8px 8px",
				padding: "6px 12px",
			},
		},
	};

	const handleLogout = () => logoutMutation.mutate();
	const fullName = user
		? `${user.first_name} ${user.last_name}`.trim() || user.username
		: "";
	const username = user?.username?.trim() || "";
	const userRole = user?.role || "Ui Ux Designer";
	const profileImage = user?.profile_pic_url || "";
	const avatarInitials = useMemo(() => {
		const source = fullName || username || user?.email || "User";
		const words = source.split(/\s+/).filter(Boolean);
		if (!words.length) return "U";
		if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
		return `${words[0][0] || ""}${words[1][0] || ""}`.toUpperCase();
	}, [fullName, username, user?.email]);

	const { data: categoriesData } = useQuery(getMarketplaceCategoriesQueryOptions());

	const CATEGORY_META: Record<number, { icon: string; description: string; image: string }> = {
		1: {
			icon: cloudIcon,
			description: "Unlocks industry specific transformation by deploying AI agents that optimize supply chains, generate actionable customer insights, and enhance operational efficiency through intelligent automation.",
			image: img1,
		},
		2: {
			icon: connectCircuitIcon,
			description: "Industrial AI Agents unify Computer Vision, IOT, and Industry specific intelligence into curated autonomous agents for real-time operational optimization.",
			image: img2,
		},
		3: {
			icon: layersIcon,
			description: "Strengthens data infrastructure and governance by enabling seamless data migration and ensuring high-quality, validated data pipelines through specialized data engineering agents.",
			image: img3,
		},
		4: {
			icon: codeIcon,
			description: "Empowers enterprises to accelerate digital initiatives by automating critical development workflows such as ETL migration, code conversion, document generation, and code creation using intelligent productivity agents.",
			image: img4,
		},
	};

	const browseSections = (categoriesData ?? []).map((cat) => ({
		id: cat.category_id,
		label: cat.category_name,
		count: cat.agent_count,
		...(CATEGORY_META[cat.category_id] ?? { icon: cloudIcon, description: cat.description, image: img1 }),
	}));

	const visibleBrowseIndices = useMemo(() => {
		if (activeBrowseIndex === null) {
			return browseSections.map((_, idx) => idx);
		}
		const lastIndex = Math.max(browseSections.length - 1, 0);
		if (browseSections.length <= 2) {
			return browseSections.map((_, idx) => idx);
		}
		if (activeBrowseIndex >= lastIndex) {
			return [lastIndex - 1, lastIndex];
		}
		return [activeBrowseIndex, activeBrowseIndex + 1];
	}, [activeBrowseIndex, browseSections]);

	const handleBrowseRowClick = (isOpen: boolean, index: number) => {
		if (isOpen) {
			setActiveBrowseIndex(null);
			return;
		}
		setActiveBrowseIndex(index);
	};

	const meta = useRouteMeta();
	const backLink = useMemo(
		() => meta?.backButtonConfig?.link?.replace(/:(\w+)/g, (_, key) => params[key] ?? key),
		[meta?.backButtonConfig?.link, params]
	);

	useEffect(() => {
		const handleOutsideClick = (event: MouseEvent) => {
			const target = event.target as Node;
			const clickedInsideBrowse =
				browseMenuRef.current?.contains(target) ?? false;
			const clickedInsideProfile =
				profileMenuRef.current?.contains(target) ?? false;

			if (!clickedInsideBrowse && !clickedInsideProfile) {
				setBrowseMenuOpen(false);
				setDropdownOpen(false);
			}
		};

		document.addEventListener("mousedown", handleOutsideClick);
		return () => {
			document.removeEventListener("mousedown", handleOutsideClick);
		};
	}, []);

	return (
		<header className="flex items-center shadow-[0_1px_5px_0_rgba(0,0,0,0.10)] backdrop-blur-[12px] border-b-[1.5px] border-b-white border-solid bg-[rgba(255,255,255,0.34)] sticky top-0 left-0 z-30 h-[60px] justify-between px-[38px] py-[11px]">
			{showMenuButton && (
				<button
					type="button"
					onClick={onMenuToggle}
					aria-label="Toggle menu"
					className="p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors lg:hidden"
				>
					<MenuRoundedIcon sx={{ fontSize: 20 }} />
				</button>
			)}

			<div className="flex-1 min-w-0 flex flex-row gap-[20px] items-center">
				<div onClick={() => navigate("/dashboard")} className="flex items-center gap-2 cursor-pointer w-max">
					<img
						src={headerWeave}
						alt="Weave Agents"
						className="cursor-pointer"
						width={100}
					/>
				</div>

				{!!meta?.backButtonConfig?.enabled && (
					<>
						<div className="h-6 w-px bg-black/15"></div>

						<Button
							sx={{
								fontSize: '13px',
								fontWeight: 700
							}}
							startIcon={<ChevronLeft />}
							component={Link}
							to={backLink ?? '/'}
							replace
							className="font-semibold leading-[1.1] uppercase text-black"
						>
							{meta?.backButtonConfig?.label}
						</Button>
					</>
				)}
			</div>

			<div className="flex items-center justify-end gap-[20px]">
				<div className="relative" ref={browseMenuRef}>
					<button
						type="button"
						onClick={() => {
							setBrowseMenuOpen((open) => !open);
							setDropdownOpen(false);
							setActiveBrowseIndex(null);
						}}
						className="group flex h-10 cursor-pointer items-center gap-[6px] rounded-[10px] px-2.5 transition-colors"
					>
						<span className="text-[13px] font-semibold leading-[1.1] uppercase text-black">
							Browse agents
						</span>
						<span className="relative flex h-[39px] w-[39px] cursor-pointer items-center justify-center overflow-hidden rounded-full">
							<img
								src={dotSquare}
								alt=""
								aria-hidden="true"
								className="absolute h-[26px] w-[26px] transition-all duration-300 ease-out group-hover:scale-90 group-hover:opacity-0 group-hover:rotate-12"
							/>
							<img
								src={dotCircle}
								alt=""
								aria-hidden="true"
								className="absolute h-[26px] w-[26px] opacity-0 transition-all duration-300 ease-out group-hover:scale-100 group-hover:opacity-100 group-hover:rotate-0 scale-90 -rotate-12"
							/>
						</span>
					</button>

					{browseMenuOpen && (
						<div
							role="menu"
							aria-label="Browse agent categories"
							className="absolute right-0 top-full mt-2 z-20 w-[435px] max-w-[calc(100vw-20px)] overflow-hidden rounded-[14px] border border-[rgba(255,255,255,0.9)] shadow-[0px_6px_15px_0px_rgba(0,0,0,0.22)]"
							style={{
								backgroundImage:
									"linear-gradient(90deg, rgba(255,255,255,0.18) 0%, rgba(255,255,255,0.18) 100%), linear-gradient(135deg, #E7D793 0%, #ECE9DC 58%, #F2F2F2 100%)",
							}}
						>
							<div className="relative pl-1.5 pr-0 py-1.5">
								{browseSections.map((section, localIndex) => {
									if (!visibleBrowseIndices.includes(localIndex)) return null;
									const isOpen = activeBrowseIndex === localIndex;
									return (
										<div key={section.label}>
											<div
												className="group flex w-full cursor-pointer items-center gap-2.5 rounded-[8px] px-3 py-2.5 transition-colors hover:bg-black/[0.04]"
												onClick={() => handleBrowseRowClick(isOpen, localIndex)}
											>
												<button
													type="button"
													role="menuitem"
													className="flex min-w-0 flex-1 cursor-pointer items-center gap-2.5 text-left"
												>
													<img src={section.icon} alt="" aria-hidden="true" className="h-5 w-5 shrink-0" />
													<span className="min-w-0 flex-1 text-[13px] font-semibold leading-none text-black">
														{section.label}
													</span>
												</button>
												<div className="ml-3 flex shrink-0 items-center">
													<span className="inline-flex items-center gap-1 rounded-[7px] border border-[#CBB355] bg-[#E2CD78] px-2 py-[3px] text-[9.5px] font-bold uppercase tracking-[0.24px] text-black">
														{section.count} agents
														<AnimatePresence initial={false}>
															{isOpen && (
																<motion.button
																	type="button"
																	aria-label={`Go to ${section.label}`}
																	onClick={(event) => {
																		event.stopPropagation();
																		agentsResetPending.add(section.id);
																		navigate(`/dashboard/${section.id}/agents`);
																		setBrowseMenuOpen(false);
																		setActiveBrowseIndex(null);
																	}}
																	initial={{ x: 8, opacity: 0 }}
																	animate={{ x: 0, opacity: 1 }}
																	exit={{ x: 8, opacity: 0 }}
																	transition={{ duration: 0.3, ease: "easeInOut" }}
																	className="ml-0.5 inline-flex h-[10px] w-[11px] cursor-pointer items-center justify-center"
																>
																	<img src={nextArrowIcon} alt="" aria-hidden="true" className="h-[10px] w-[11px]" />
																</motion.button>
															)}
														</AnimatePresence>
													</span>
												</div>
											</div>

											<AnimatePresence initial={false}>
												{isOpen && (
													<motion.div
														key={`${section.label}-expanded`}
														initial={{ y: 60, opacity: 0 }}
														animate={{ y: 0, opacity: 1 }}
														exit={{ y: -40, opacity: 0 }}
														transition={{ duration: 0.38, ease: [0.22, 1, 0.36, 1] }}
														className="relative min-h-[140px] px-3"
													>
														<div className="relative z-10 w-[58%] pt-[12px] pr-1">
															<p className="w-full text-[11px] leading-[1.8] text-black/90">
																{section.description}
															</p>
														</div>
														<div
															role="img"
															aria-label={`${section.label} visual`}
															className="pointer-events-none absolute inset-y-0 right-0 z-0 w-[45%] bg-contain bg-center bg-no-repeat"
															style={{
																backgroundImage: `url(${section.image})`,
																WebkitMaskImage: "linear-gradient(to right, transparent 0%, black 30%)",
																maskImage: "linear-gradient(to right, transparent 0%, black 30%)",
															}}
														/>
													</motion.div>
												)}
											</AnimatePresence>

											{localIndex < browseSections.length - 1 && (
												<div className="mx-4 mt-2 mb-1 h-px bg-black/10" />
											)}
										</div>
									);
								})}
							</div>
						</div>
					)}
				</div>
				<div className="h-6 w-px bg-black/15" />
				<Tooltip
					title="Help & Support"
					placement="bottom"
					enterDelay={150}
					slotProps={headerTooltipSlotProps}
				>
					<button
						type="button"
						aria-label="Help"
						className="flex h-8 w-8 cursor-pointer items-center justify-center rounded-[8px] transition-colors hover:bg-black/[0.08]"
						onMouseEnter={() => setHelpActive(true)}
						onMouseLeave={() => setHelpActive(false)}
						onFocus={() => setHelpActive(true)}
						onBlur={() => setHelpActive(false)}
					>
						<SmartAnimateIconContainer active={helpActive}>
							<img
								src={question}
								alt="Help"
								className="h-4.5 w-4.5"
							/>
						</SmartAnimateIconContainer>
					</button>
				</Tooltip>
				<div className="h-6 w-px bg-black/15" />

				<div className="relative" ref={profileMenuRef}>
					<Tooltip
						title="My Profile"
						placement="bottom"
						enterDelay={150}
						open={profileTooltipOpen && !dropdownOpen}
						disableInteractive
						disableHoverListener
						disableFocusListener
						disableTouchListener={dropdownOpen}
						slotProps={headerTooltipSlotProps}
					>
						<button
							type="button"
							onClick={() => {
								setProfileTooltipOpen(false);
								setDropdownOpen((o) => !o);
								setBrowseMenuOpen(false);
							}}
							onMouseEnter={() => {
								setProfileHover(true);
								if (!dropdownOpen) setProfileTooltipOpen(true);
							}}
							onMouseLeave={() => {
								setProfileHover(false);
								setProfileTooltipOpen(false);
							}}
							onFocus={() => {
								setProfileHover(true);
								if (!dropdownOpen) setProfileTooltipOpen(true);
							}}
							onBlur={() => {
								setProfileHover(false);
								setProfileTooltipOpen(false);
							}}
							aria-expanded={dropdownOpen}
							aria-haspopup="menu"
							aria-label="User menu"
							className="flex items-center rounded-[999px] p-0.5 transition-colors hover:bg-black/[0.03]"
						>
							<motion.span
								className="relative inline-flex h-10 w-10 items-center justify-center"
								animate={{
									x: profileHover || dropdownOpen ? -0.9 : 0,
									y: profileHover || dropdownOpen ? 0.9 : 0,
								}}
								transition={{ duration: 0.3, ease: "easeInOut" }}
							>
								<motion.span
									aria-hidden="true"
									className="pointer-events-none absolute h-10 w-10 rounded-full"
									animate={{
										opacity: profileHover || dropdownOpen ? 1 : 0,
										scale: profileHover || dropdownOpen ? 1 : 0.94,
										backgroundColor: profileHover || dropdownOpen ? "rgba(0,0,0,0.08)" : "rgba(0,0,0,0)",
									}}
									transition={{ duration: 0.3, ease: "easeInOut" }}
								/>
								<motion.span
									aria-hidden="true"
									className="pointer-events-none absolute z-20 h-9 w-9 rounded-full"
									animate={{
										opacity: profileHover || dropdownOpen ? 1 : 0,
										scale: profileHover || dropdownOpen ? 1 : 0.92,
										background: profileHover || dropdownOpen
											? "radial-gradient(circle at center, rgba(255,255,255,0.2) 0%, rgba(255,255,255,0.1) 24%, rgba(255,255,255,0.03) 38%, rgba(0,0,0,0.5) 100%)"
											: "radial-gradient(circle at center, rgba(255,255,255,0) 0%, rgba(255,255,255,0) 100%)",
									}}
									transition={{ duration: 0.3, ease: "easeInOut" }}
								/>
								{profileImage ? (
									<img
										src={profileImage}
										alt={fullName || username || "User profile"}
										className="relative z-10 h-9 w-9 cursor-pointer rounded-full object-cover"
									/>
								) : (
									<span className="relative z-10 inline-flex h-9 w-9 items-center justify-center rounded-full bg-[#E2CD78] text-[11px] font-bold text-black">
										{avatarInitials}
									</span>
								)}
							</motion.span>
						</button>
					</Tooltip>

					{dropdownOpen && (
						<>
							<div
								role="menu"
								aria-label="User menu"
								className="absolute right-0 top-full mt-2 z-20 w-[316px] max-w-[calc(100vw-20px)] overflow-hidden rounded-[14px] border border-[rgba(255,255,255,0.9)] shadow-[0px_6px_15px_0px_rgba(0,0,0,0.22)]"
								style={{
									backgroundImage:
										"linear-gradient(90deg, rgba(255,255,255,0.2) 0%, rgba(255,255,255,0.2) 100%), linear-gradient(330.45deg, #EDEDED 52.87%, #E3D693 97.2%)",
								}}
							>
								<img
									src={waveAgentLetter}
									alt=""
									aria-hidden="true"
									className="pointer-events-none absolute -right-8 -top-10 h-36 w-36 opacity-35"
								/>

								<div className="relative px-3.5 pt-3.5 pb-3">
									<div className="flex items-center gap-2.5">
										{profileImage ? (
											<img
												src={profileImage}
												alt={fullName || username || "Profile"}
												className="h-9 w-9 rounded-full object-cover"
											/>
										) : (
											<span className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-[#E2CD78] text-[11px] font-bold text-black">
												{avatarInitials}
											</span>
										)}
										<div className="min-w-0">
											<p className="truncate text-[14px] leading-[20px] font-semibold text-black uppercase">
												{fullName || username || "User"}
											</p>
											<p className="truncate text-[12.5px] font-bold text-[#846C00]">
												{userRole}
											</p>
										</div>
									</div>
								</div>

								<div className="relative pb-2">
									<MenuOption
										icon={settingsIcon}
										label="AGENT SETTINGS"
										onClick={() => {
											setDropdownOpen(false);
										}}
										arrowIcon={nextArrowIcon}
									/>
									<MenuOption
										icon={logoutIcon}
										label="LOG OUT"
										onClick={handleLogout}
										arrowIcon={nextArrowIcon}
									/>
								</div>
							</div>
						</>
					)}
				</div>
			</div>
		</header>
	);
};

const MenuOption = ({
	icon,
	label,
	onClick,
	arrowIcon,
}: {
	icon: string;
	label: string;
	onClick: () => void;
	arrowIcon: string;
}) => (
	<button
		type="button"
		role="menuitem"
		onClick={onClick}
		className="group mb-1.5 flex h-9 w-full cursor-pointer items-center justify-between rounded-none px-3.5 transition-colors"
	>
		<div className="flex h-full items-center gap-2.5">
			<img src={icon} alt="" className="h-4.5 w-4.5 shrink-0" aria-hidden="true" />
			<span className="text-[12.5px] leading-none font-semibold uppercase text-black">
				{label}
			</span>
		</div>
		<img
			src={arrowIcon}
			alt=""
			className="h-3 w-3.5 shrink-0 transition-transform duration-200 group-hover:translate-x-0.5"
			aria-hidden="true"
		/>
	</button>
);

const SmartAnimateIconContainer = ({
	active,
	blinkOnActive = false,
	children,
}: {
	active: boolean;
	blinkOnActive?: boolean;
	children: ReactNode;
}) => {
	const frameSizeClass = "h-8 w-8";

	return (
		<span className={`relative inline-flex items-center justify-center overflow-visible ${frameSizeClass}`}>
			<motion.span
				aria-hidden="true"
				className="pointer-events-none absolute h-8 w-8 rounded-[10px] bg-black/[0.05]"
				animate={{
					opacity: active ? 1 : 0,
					scale: active ? 1.03 : 0.95,
				}}
				transition={{ duration: 0.3, ease: "easeInOut" }}
			/>
			<motion.span
				className="relative z-10 inline-flex items-center justify-center"
				animate={{
					scale: active ? 1.04 : 1,
					filter: active
						? "brightness(0) saturate(100%) contrast(1.12)"
						: "brightness(0) saturate(100%) contrast(1)",
					opacity: blinkOnActive && active ? [1, 0.32, 1] : 1,
				}}
				transition={{
					duration: 0.3,
					ease: "easeInOut",
					times: blinkOnActive && active ? [0, 0.45, 1] : undefined,
				}}
			>
				{children}
			</motion.span>
		</span>
	);
};
```
