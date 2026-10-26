"use client";

import React from "react";
import {
  BellIcon,
  CategoriesIcon,
  DashboardIcon,
  ExportIcon,
  HelpCircleIcon,
  LockShieldIcon,
  LogoCheckIcon,
  SettingsIcon,
  TransactionsIcon,
  UploadCloudIcon,
} from "./Icons";

interface SidebarProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
  onOpenUpload: () => void;
}

export function Sidebar({ currentTab, onSelectTab, onOpenUpload }: SidebarProps) {
  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: <DashboardIcon size={18} /> },
    {
      id: "upload",
      label: "Upload Statement",
      icon: <UploadCloudIcon size={18} />,
      onClick: onOpenUpload,
    },
    { id: "transactions", label: "Transactions", icon: <TransactionsIcon size={18} /> },
    { id: "categories", label: "Categories", icon: <CategoriesIcon size={18} /> },
    { id: "export", label: "Export Reports", icon: <ExportIcon size={18} /> },
    { id: "settings", label: "Settings", icon: <SettingsIcon size={18} /> },
  ];

  return (
    <aside className="sidebar">
      {/* Brand Header */}
      <div className="sidebar-brand">
        <div className="brand-icon-box">
          <LogoCheckIcon size={20} />
        </div>
        <span className="brand-title">TaxSort</span>
        <span className="brand-pill">Helper</span>
      </div>

      {/* Nav Section */}
      <div className="sidebar-section-title">Tax Workspace</div>
      <nav className="sidebar-nav">
        {navItems.map((item) => {
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => {
                if (item.onClick) {
                  item.onClick();
                } else {
                  onSelectTab(item.id);
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

      {/* Sidebar Footer */}
      <div className="sidebar-bottom">
        <div className="security-pill">
          <LockShieldIcon size={15} />
          <span>Data encrypted & private</span>
        </div>

        <button className="nav-link" style={{ padding: "6px 8px" }}>
          <HelpCircleIcon size={16} />
          <span>Help & Support</span>
        </button>

        <div className="user-profile-badge">
          <div className="user-avatar">
            <span>TF</span>
          </div>
          <div className="user-info">
            <span className="user-name">Tax Filer</span>
            <span className="user-subtext">Personal Account</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
