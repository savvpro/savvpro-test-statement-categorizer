"use client";

import React, { useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import {
  BellIcon,
  CategoriesIcon,
  DashboardIcon,
  ExportIcon,
  FolderIcon,
  HelpCircleIcon,
  LockShieldIcon,
  LogoCheckIcon,
  SettingsIcon,
  TransactionsIcon,
  UploadCloudIcon,
} from "./Icons";
import { UploadModal } from "./UploadModal";
import { useAuth } from "../context/AuthContext";

interface AppShellProps {
  children: React.ReactNode;
  pageTitle?: string;
  pageSubtitle?: string;
  onStatementUploaded?: (data?: unknown) => void;
}

export function AppShell({
  children,
  pageTitle,
  pageSubtitle,
  onStatementUploaded,
}: AppShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const [uploadOpen, setUploadOpen] = useState(false);
  const [profileMenuOpen, setProfileMenuOpen] = useState(false);

  interface NavItem {
    href: string;
    label: string;
    icon: React.ReactNode;
    onClick?: () => void;
  }

  const navItems: NavItem[] = [
    { href: "/", label: "Dashboard", icon: <DashboardIcon size={18} /> },
    { href: "/upload", label: "Upload Statement", icon: <UploadCloudIcon size={18} /> },
    { href: "/transactions", label: "Transactions", icon: <TransactionsIcon size={18} /> },
    { href: "/categories", label: "Categories", icon: <CategoriesIcon size={18} /> },
    { href: "/export", label: "Export Reports", icon: <ExportIcon size={18} /> },
    { href: "/settings", label: "Settings", icon: <SettingsIcon size={18} /> },
  ];

  // Derive breadcrumb label
  const getBreadcrumbName = () => {
    if (pathname === "/") return "Overview";
    if (pathname === "/transactions") return "Transactions";
    if (pathname === "/categories") return "Categories";
    if (pathname === "/export") return "Export Reports";
    if (pathname === "/settings") return "Settings";
    if (pathname === "/upload") return "Upload Statement";
    return "Overview";
  };

  const displayName = user?.full_name || "Tax Filer";
  const userInitials = displayName
    .split(" ")
    .map((n) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <div className="app-container">
      {/* ── Left Sidebar ── */}
      <aside className="sidebar">
        {/* Brand */}
        <div
          className="sidebar-brand"
          style={{ cursor: "pointer" }}
          onClick={() => router.push("/")}
        >
          <div className="brand-icon-box">
            <LogoCheckIcon size={20} />
          </div>
          <span className="brand-title">TaxSort</span>
          <span className="brand-pill">Helper</span>
        </div>

        {/* Navigation */}
        <div className="sidebar-section-title">Tax Workspace</div>
        <nav className="sidebar-nav">
          {navItems.map((item) => {
            const isActive =
              item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);

            return (
              <button
                key={item.label}
                onClick={() => {
                  if (item.onClick) {
                    item.onClick();
                  } else {
                    router.push(item.href);
                  }
                }}
                className={`nav-link ${isActive ? "active" : ""}`}
              >
                {item.icon}
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Bottom */}
        <div className="sidebar-bottom">
          <div className="security-pill">
            <LockShieldIcon size={15} />
            <span>Data encrypted & private</span>
          </div>

          <button
            className="nav-link"
            style={{ padding: "6px 8px" }}
            onClick={() => alert("Help documentation: IRS Schedule C guidelines & TaxSort engine rules.")}
          >
            <HelpCircleIcon size={16} />
            <span>Help & Support</span>
          </button>

          <div
            className="user-profile-badge"
            style={{ cursor: "pointer", position: "relative" }}
            onClick={() => setProfileMenuOpen(!profileMenuOpen)}
          >
            <div className="user-avatar">
              <span>{userInitials}</span>
            </div>
            <div className="user-info">
              <span className="user-name">{displayName}</span>
              <span className="user-subtext">{user?.email || "Personal Account"}</span>
            </div>

            {profileMenuOpen && (
              <div
                style={{
                  position: "absolute",
                  bottom: "100%",
                  left: 0,
                  width: "100%",
                  background: "#1e293b",
                  border: "1px solid #334155",
                  borderRadius: 8,
                  padding: "6px",
                  boxShadow: "0 10px 15px -3px rgba(0,0,0,0.3)",
                  marginBottom: 8,
                  zIndex: 50,
                }}
              >
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    logout();
                  }}
                  style={{
                    width: "100%",
                    textAlign: "left",
                    padding: "8px 10px",
                    color: "#f87171",
                    fontSize: 13,
                    fontWeight: 600,
                    borderRadius: 6,
                    background: "transparent",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "#334155")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                >
                  Sign Out
                </button>
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* ── Main Workspace ── */}
      <div className="main-wrapper">
        {/* Top Header */}
        <header className="top-bar">
          <div className="breadcrumbs">
            <FolderIcon size={16} />
            <span>Tax Workspace</span>
            <span>/</span>
            <span className="breadcrumbs-current">{getBreadcrumbName()}</span>
          </div>

          <div className="top-bar-right">
            <div className="tax-year-pill">
              <span className="status-dot-green" />
              <span>Tax Year 2026</span>
            </div>

            <button
              className="top-upload-btn"
              onClick={() => setUploadOpen(true)}
            >
              <UploadCloudIcon size={16} />
              <span>Upload Statement</span>
            </button>

            <button
              className="icon-btn"
              aria-label="Notifications"
              onClick={() => alert("All statements up to date. No pending system notices.")}
            >
              <BellIcon size={18} />
              <span className="notif-dot" />
            </button>

            <div
              className="user-avatar"
              style={{ width: 32, height: 32, cursor: "pointer" }}
              onClick={() => setProfileMenuOpen(!profileMenuOpen)}
            >
              <span>{userInitials}</span>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="page-container">
          {pageTitle && (
            <div className="header-banner">
              <div>
                <h1 className="page-title">{pageTitle}</h1>
                {pageSubtitle && (
                  <p className="page-subtitle">{pageSubtitle}</p>
                )}
              </div>
            </div>
          )}

          {children}
        </main>
      </div>

      {/* ── Global Upload Modal ── */}
      <UploadModal
        isOpen={uploadOpen}
        onClose={() => setUploadOpen(false)}
        onSuccess={(data) => {
          if (onStatementUploaded) onStatementUploaded(data);
          router.refresh();
        }}
      />
    </div>
  );
}
