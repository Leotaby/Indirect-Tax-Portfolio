indirect-tax-portfolio/
├── data/
│   └── indirect_tax.db        # SQLite database with VAT rates & sample transactions
├── notebooks/
│   └── indirect_tax_portfolio.ipynb  # Jupyter notebook demonstrating all steps
├── reports/
│   └── vat_q1_2025_report.xlsx # Generated Excel report for Q1 2025 VAT summary
├── scripts/
│   ├── create_db.py           # Script to create and populate the database
│   ├── calculate_vat.py       # Script to compute VAT liabilities and reconciliation
│   └── export_report.py       # Script to export summary and reconciliation to Excel
├── requirements.txt           # Python dependencies (pandas, sqlite3, openpyxl)
└── README.md                  # This documentation
