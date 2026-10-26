"use client";

import React from "react";
import { BellIcon, FolderIcon, UploadCloudIcon } from "./Icons";

interface HeaderProps {
  currentTabName: string;
  onOpenUpload: () => void;
}

export function Header({ currentTabName, onOpenUpload }: HeaderProps) {
  return (
    <header className="top-bar">
      <div className="breadcrumbs">
        <FolderIcon size={16} />
        <span>Tax Workspace</span>
        <span>/</span>
        <span className="breadcrumbs-current">{currentTabName}</span>
      </div>

      <div className="top-bar-right">
        <div className="tax-year-pill">
          <span className="status-dot-green" />
          <span>Tax Year 2026</span>
        </div>

        <button className="top-upload-btn" onClick={onOpenUpload}>
          <UploadCloudIcon size={16} />
          <span>Upload Statement</span>
        </button>

        <button className="icon-btn" aria-label="Notifications">
          <BellIcon size={18} />
          <span className="notif-dot" />
        </button>

        <div className="user-avatar" style={{ width: 32, height: 32, cursor: "pointer" }}>
          <span>TF</span>
        </div>
      </div>
    </header>
  );
}
