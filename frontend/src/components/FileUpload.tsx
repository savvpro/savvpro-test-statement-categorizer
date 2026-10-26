import React, { useRef, useState } from "react";
import { UploadCloud, FileText, AlertCircle, Sparkles } from "lucide-react";

interface FileUploadProps {
  onFileSelected: (file: File) => void;
  isLoading: boolean;
  error: string | null;
}

export const FileUpload: React.FC<FileUploadProps> = ({
  onFileSelected,
  isLoading,
  error,
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onFileSelected(e.dataTransfer.files[0]);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onFileSelected(e.target.files[0]);
    }
  };

  const loadSample = async (samplePath: string, filename: string) => {
    try {
      // In local dev, fetch the sample data from backend or bundled text
      const sampleContent = await getSampleContent(filename);
      const file = new File([sampleContent], filename, { type: "text/csv" });
      onFileSelected(file);
    } catch (err) {
      console.error("Failed to load sample:", err);
    }
  };

  return (
    <div className="upload-container">
      <div
        className={`drop-zone ${isDragOver ? "drag-over" : ""} ${
          isLoading ? "loading" : ""
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !isLoading && fileInputRef.current?.click()}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileInput}
          accept=".csv,.txt"
          style={{ display: "none" }}
        />
        <div className="drop-content">
          <div className="icon-wrapper">
            <UploadCloud size={44} className="upload-icon" />
          </div>
          <h3>Upload Business Bank or Credit Card Statement</h3>
          <p className="subtitle">
            Drag & drop your statement CSV here, or click to browse
          </p>
          <div className="file-hints">
            <span>Supports CSV & TXT</span>
            <span>•</span>
            <span>Up to 10 MB</span>
            <span>•</span>
            <span>Auto-detects delimiters & date formats</span>
          </div>
        </div>
      </div>

      {error && (
        <div className="error-banner">
          <AlertCircle size={20} className="error-icon" />
          <div className="error-text">
            <strong>Statement Processing Error:</strong> {error}
          </div>
        </div>
      )}

      <div className="sample-section">
        <div className="sample-label">
          <Sparkles size={16} />
          <span>Or test with pre-built realistic sample statements:</span>
        </div>
        <div className="sample-buttons">
          <button
            type="button"
            className="sample-btn"
            disabled={isLoading}
            onClick={() =>
              loadSample(
                "clean_business_credit_card.csv",
                "clean_business_credit_card.csv"
              )
            }
          >
            <FileText size={14} /> Clean Business Credit Card
          </button>
          <button
            type="button"
            className="sample-btn"
            disabled={isLoading}
            onClick={() =>
              loadSample(
                "messy_checking_statement.csv",
                "messy_checking_statement.csv"
              )
            }
          >
            <FileText size={14} /> Messy Bank Checking (Preamble & Fees)
          </button>
          <button
            type="button"
            className="sample-btn"
            disabled={isLoading}
            onClick={() =>
              loadSample(
                "edge_cases_and_refunds.csv",
                "edge_cases_and_refunds.csv"
              )
            }
          >
            <FileText size={14} /> Edge Cases (Refunds, Transfers & Duplicates)
          </button>
        </div>
      </div>
    </div>
  );
};

// Fallback embedded samples for instant browser testing without filesystem path reliance
async function getSampleContent(filename: string): Promise<string> {
  if (filename.includes("clean")) {
    return `Transaction Date,Description,Amount
2024-03-01,GITHUB INC 800-826-0428,21.00
2024-03-02,JETBRAINS S.R.O. PRAGUE,149.00
2024-03-03,VERCEL PRO HOSTING,20.00
2024-03-05,AWS AMAZON WEB SERVICES,184.50
2024-03-08,FIGMA MONTHLY SEATS,15.00
2024-03-10,SLACK TECHNOLOGIES,8.75
2024-03-12,GOOGLE CLOUD STORAGE,42.10
2024-03-15,1PASSWORD SUBSCRIPTION,7.99
2024-03-18,ZOOM.US MONTHLY,15.99
2024-03-20,DIGITALOCEAN DROPLET,24.00
2024-03-22,APPLE STORE #104 MACBOOK ADAPTER,49.00
2024-03-24,UBER *TRIP 1492 RIDESHARE,32.40
2024-03-26,GUSTO PAYROLL SERVICES,45.00
2024-03-28,INTUIT QUICKBOOKS ONLINE,30.00
2024-03-29,STARLINK INTERNET SVC,110.00
2024-03-30,POSTMAN PRO TEAM,29.00`;
  }
  if (filename.includes("messy")) {
    return `Apex Horizon Tech LLC - Business Operating Checking
Account Ending in: 4892
Statement Period: 03/01/2024 to 03/31/2024

Date;Description;Amount
03/01/2024;DIRECT DEP - STRIPE PAYOUT PPD ID: 9482910;"$4,850.00"
03/03/2024;POS PURCHASE CHECKCARD 0303 GITHUB INC *SUITE 400 SAN FRANCISCO CA 94107 US;"-$21.00"
03/05/2024;PAYPAL *HEROKU 4029357733 CA REF#99824;"-$50.00"
03/07/2024;SQ *BLUE BOTTLE COFFEE #104 AUSTIN TX;"-$6.75"
03/10/2024;PURCHASE AUTHORIZED ON 03/09 APPLE.COM/BILL 800-275-2273 CA S4920491829;"-$199.00"
03/12/2024;ACH CREDIT - CLIENT INVOICE INV-2024-032;"$3,200.00"
03/15/2024;MONTHLY MAINTENANCE FEE;"-$15.00"
03/16/2024;FOREIGN TRANSACTION FEE - EUR CONVERSION;"-$4.25"
03/18/2024;CLOUDFLARE INC NETWORKING;"-$20.00"
03/22/2024;TST* CANTEEN CAFE - NEW YORK NY STORE 12;"-$18.50"
03/25/2024;WIRE TRANSFER OUTGOING FEE - DOMESTIC;"-$25.00"
03/28/2024;ONLINE BANKING TRANSFER TO SAVINGS ACCT 8812;"-$1,500.00"
03/30/2024;AUTOMATIC PAYMENT - THANK YOU CREDIT CARD;"-$840.00"

Ending Balance: $12,450.50
Total Debits: $2,700.50
Total Credits: $8,050.00`;
  }
  return `Date,Description,Debit,Credit
2024-03-02,AWS AMAZON WEB SERVICES CLOUD,185.00,
2024-03-05,AWS AMAZON WEB SERVICES REFUND,,185.00
2024-03-07,FIGMA DESIGN SEAT,15.00,
2024-03-07,FIGMA DESIGN SEAT,15.00,
2024-03-10,AMAZON.COM*2K489 BILL ORDER 1092,68.40,
2024-03-12,TARGET STORE #0482 SUPPLIES,42.15,
2024-03-14,COSTCO WHOLESALE WAREHOUSE,124.80,
2024-03-16,CORNER BAKERY CAFE LUNCH,24.50,
2024-03-18,ONLINE TRANSFER TO SAVINGS,2000.00,
2024-03-20,CREDIT CARD AUTOPAY PAYMENT THANK YOU,,750.00
2024-03-22,JETBRAINS IDE LICENSE,149.00,
2024-03-24,STRIPE PAYOUT CLIENT DEPOSIT,,3400.00
2024-03-26,RANDOM UNKNOWN LOCAL TECH REPAIR,85.00,`;
}
