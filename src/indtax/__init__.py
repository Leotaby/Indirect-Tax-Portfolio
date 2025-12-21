"""
Indirect Tax Portfolio - EMEA VAT Automation Toolkit

A comprehensive Python package for automating indirect tax processes:
- VAT liability calculations across EU/EMEA jurisdictions
- Payment reconciliation with tolerance matching
- VAT return generation and EC Sales List reporting
- Data validation with country-specific VAT number checks

Author: Hatef Tabbakhian
License: MIT
"""

from .vat_calculator import (
    VATCalculator,
    VATRate,
    Transaction,
    VATCalculation,
    CountryVATRates,
    EU_VAT_RATES,
    calculate_reverse_charge_applicable,
)

from .reconciliation import (
    PaymentReconciler,
    Invoice,
    Payment,
    MatchResult,
    MatchStatus,
    ReconciliationReport,
    Currency,
    generate_aging_report,
)

from .reporting import (
    VATReturnGenerator,
    VATReturn,
    VATReturnLine,
    ECSalesList,
    ECSalesLine,
    ReportExporter,
    ReportFormat,
    ReportPeriod,
    generate_vat_summary_pivot,
)

from .validation import (
    VATNumberValidator,
    TransactionValidator,
    ValidationResult,
    ValidationReport,
    ValidationSeverity,
    validate_vat_calculation,
    VAT_PATTERNS,
)

__version__ = "1.0.0"
__author__ = "Hatef Tabbakhian"

__all__ = [
    # VAT Calculator
    "VATCalculator",
    "VATRate",
    "Transaction",
    "VATCalculation",
    "CountryVATRates",
    "EU_VAT_RATES",
    "calculate_reverse_charge_applicable",
    # Reconciliation
    "PaymentReconciler",
    "Invoice",
    "Payment",
    "MatchResult",
    "MatchStatus",
    "ReconciliationReport",
    "Currency",
    "generate_aging_report",
    # Reporting
    "VATReturnGenerator",
    "VATReturn",
    "VATReturnLine",
    "ECSalesList",
    "ECSalesLine",
    "ReportExporter",
    "ReportFormat",
    "ReportPeriod",
    "generate_vat_summary_pivot",
    # Validation
    "VATNumberValidator",
    "TransactionValidator",
    "ValidationResult",
    "ValidationReport",
    "ValidationSeverity",
    "validate_vat_calculation",
    "VAT_PATTERNS",
]
