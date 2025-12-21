# 🧾 Indirect Tax Automation Portfolio

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-Passing-brightgreen.svg)]()

> **EMEA VAT automation toolkit** — Calculate VAT liabilities, reconcile payments, validate data, and generate compliance reports across 30+ European jurisdictions.

---

## 🎯 Overview

A comprehensive Python package for automating indirect tax processes, designed for:

- **Tax Teams** — Automate VAT calculations and return preparation
- **Finance Teams** — Reconcile payments to invoices with tolerance matching
- **Compliance Teams** — Validate VAT numbers and transaction data
- **Developers** — Integrate tax logic into ERP/accounting systems

## ✨ Features

| Module | Description |
|--------|-------------|
| **VAT Calculator** | Calculate VAT for 30+ EU/EMEA countries with standard, reduced, and zero rates |
| **Payment Reconciler** | Match payments to invoices with configurable tolerance and multi-currency support |
| **Report Generator** | Generate UK VAT returns, EC Sales Lists, and custom reports |
| **Data Validator** | Validate VAT numbers against country-specific patterns and check digits |

---

## 🛠 Installation

```bash
git clone https://github.com/Leotaby/Indirect-Tax-Portfolio.git
cd Indirect-Tax-Portfolio

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -e .
```

---

## 🚀 Quick Start

### VAT Calculation

```python
from indtax import VATCalculator, Transaction, VATRate
from decimal import Decimal
from datetime import date

# Initialize calculator with EU VAT rates
calculator = VATCalculator()

# Create a transaction
transaction = Transaction(
    transaction_id="INV-2024-001",
    date=date.today(),
    country_code="DE",          # Germany
    net_amount=Decimal("1000.00"),
    rate_type=VATRate.STANDARD,  # 19%
    description="Consulting services",
)

# Calculate VAT
result = calculator.calculate_vat(transaction)

print(f"Net:   €{result.net_amount}")      # €1000.00
print(f"VAT:   €{result.vat_amount}")      # €190.00
print(f"Gross: €{result.gross_amount}")    # €1190.00
```

### Payment Reconciliation

```python
from indtax import PaymentReconciler, Invoice, Payment, Currency
from decimal import Decimal
from datetime import date

# Initialize reconciler
reconciler = PaymentReconciler(
    tolerance_amount=Decimal("0.05"),  # Accept €0.05 variance
    tolerance_percent=Decimal("0.01"), # Or 1% variance
)

# Create invoices and payments
invoices = [
    Invoice(
        invoice_id="INV001",
        invoice_date=date(2024, 1, 1),
        due_date=date(2024, 1, 31),
        customer_id="CUST001",
        currency=Currency.EUR,
        net_amount=Decimal("1000.00"),
        vat_amount=Decimal("190.00"),
        gross_amount=Decimal("1190.00"),
        country_code="DE",
    )
]

payments = [
    Payment(
        payment_id="PMT001",
        payment_date=date(2024, 1, 15),
        customer_id="CUST001",
        currency=Currency.EUR,
        amount=Decimal("1190.00"),
        reference="INV001",
    )
]

# Run reconciliation
report = reconciler.reconcile(invoices, payments)

print(f"Matched: {report.matched_count}")
print(f"Unmatched invoices: {report.unmatched_invoices}")
print(f"Unmatched payments: {report.unmatched_payments}")
```

### VAT Number Validation

```python
from indtax import VATNumberValidator

validator = VATNumberValidator()

# Validate German VAT number
result = validator.validate("DE123456789")
print(f"Valid: {result.passed}")  # True

# Validate with wrong format
result = validator.validate("XX12345")
print(f"Valid: {result.passed}")  # False
print(f"Error: {result.message}")
```

### Generate VAT Return

```python
from indtax import VATReturnGenerator, ReportExporter, ReportFormat
from pathlib import Path

# Generate UK VAT return
generator = VATReturnGenerator("GB")
vat_return = generator.generate_uk_vat_return(
    period_start=date(2024, 1, 1),
    period_end=date(2024, 3, 31),
    sales_calculations=sales_results,
    purchase_calculations=purchase_results,
)

print(f"Output VAT: £{vat_return.total_output_vat}")
print(f"Input VAT:  £{vat_return.total_input_vat}")
print(f"Net Due:    £{vat_return.net_vat_due}")

# Export to file
exporter = ReportExporter(Path("./reports"))
exporter.export_vat_return(vat_return, ReportFormat.JSON)
```

---

## 🌍 Supported Countries

VAT rates for 30+ EMEA jurisdictions:

| Country | Standard | Reduced | Super-Reduced |
|---------|----------|---------|---------------|
| 🇩🇪 Germany | 19% | 7% | - |
| 🇫🇷 France | 20% | 10% | 5.5% |
| 🇮🇹 Italy | 22% | 10% | 4% |
| 🇪🇸 Spain | 21% | 10% | 4% |
| 🇳🇱 Netherlands | 21% | 9% | - |
| 🇬🇧 UK | 20% | 5% | - |
| 🇵🇱 Poland | 23% | 8% | 5% |
| 🇸🇪 Sweden | 25% | 12% | 6% |
| ... | ... | ... | ... |

*Full list of 30+ countries in `src/indtax/vat_calculator.py`*

---

## 📁 Project Structure

```
Indirect-Tax-Portfolio/
├── src/
│   └── indtax/
│       ├── __init__.py          # Package exports
│       ├── vat_calculator.py    # VAT calculation engine
│       ├── reconciliation.py    # Payment matching
│       ├── reporting.py         # VAT returns & reports
│       └── validation.py        # Data validation
├── tests/
│   └── test_indtax.py           # Unit tests
├── data/                        # Sample data files
├── reports/                     # Generated reports
├── pyproject.toml               # Package configuration
└── README.md
```

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src/indtax --cov-report=html
```

---

## 📋 API Reference

### VATCalculator

```python
calculator = VATCalculator()

# Get rate for country
rate = calculator.get_vat_rate("DE", VATRate.STANDARD)  # Decimal("19")

# Calculate single transaction
result = calculator.calculate_vat(transaction)

# Calculate batch
results = calculator.calculate_batch([txn1, txn2, txn3])

# Get liability summary
liability = calculator.calculate_vat_liability(results, group_by_country=True)
```

### PaymentReconciler

```python
reconciler = PaymentReconciler(
    tolerance_amount=Decimal("0.05"),
    tolerance_percent=Decimal("0.01"),
)

# Set FX rates for multi-currency
reconciler.set_fx_rate(Currency.GBP, Currency.EUR, Decimal("1.17"))

# Run reconciliation
report = reconciler.reconcile(invoices, payments)
```

### VATNumberValidator

```python
validator = VATNumberValidator()
result = validator.validate("DE123456789")

# Supported formats:
# DE123456789      (Germany)
# FR12345678901    (France)  
# GB123456789      (UK)
# IT12345678901    (Italy)
# ... and 25+ more countries
```

---

## 🗺 Roadmap

- [x] VAT calculation for 30+ countries
- [x] Payment reconciliation with tolerance
- [x] VAT number format validation
- [x] UK VAT return generation
- [x] EC Sales List generation
- [ ] VIES API integration (live VAT validation)
- [ ] SAF-T export format
- [ ] Intrastat reporting
- [ ] Real-time FX rate fetching

---

## 📚 References

- [EU VAT Rates](https://ec.europa.eu/taxation_customs/vat-rates_en)
- [VIES VAT Validation](https://ec.europa.eu/taxation_customs/vies/)
- [UK VAT Guide](https://www.gov.uk/guidance/vat-guide-notice-700)

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 👤 Author

**Hatef Tabbakhian**  
MSc Economics & Finance | Tax & Financial Systems Automation

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?style=flat&logo=linkedin)](https://linkedin.com/in/hateftaby)
[![GitHub](https://img.shields.io/badge/GitHub-Follow-black?style=flat&logo=github)](https://github.com/Leotaby)
