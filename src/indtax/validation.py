"""
Data Validation Module

Validates tax data for compliance and accuracy.
Includes VAT number validation, transaction checks, and data quality rules.

Author: Hatef Tabbakhian
"""

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Callable, Any
from enum import Enum


class ValidationSeverity(Enum):
    """Severity level of validation issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationResult:
    """Result of a single validation check."""
    rule_id: str
    rule_name: str
    passed: bool
    severity: ValidationSeverity
    message: str
    field_name: Optional[str] = None
    record_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "passed": self.passed,
            "severity": self.severity.value,
            "message": self.message,
            "field": self.field_name,
            "record": self.record_id,
        }


@dataclass
class ValidationReport:
    """Summary of all validation results."""
    validated_at: date
    total_records: int
    results: List[ValidationResult] = field(default_factory=list)
    
    @property
    def error_count(self) -> int:
        return sum(
            1 for r in self.results 
            if not r.passed and r.severity == ValidationSeverity.ERROR
        )
    
    @property
    def warning_count(self) -> int:
        return sum(
            1 for r in self.results 
            if not r.passed and r.severity == ValidationSeverity.WARNING
        )
    
    @property
    def is_valid(self) -> bool:
        return self.error_count == 0
    
    def add_result(self, result: ValidationResult):
        self.results.append(result)
    
    def get_errors(self) -> List[ValidationResult]:
        return [
            r for r in self.results 
            if not r.passed and r.severity == ValidationSeverity.ERROR
        ]
    
    def get_warnings(self) -> List[ValidationResult]:
        return [
            r for r in self.results 
            if not r.passed and r.severity == ValidationSeverity.WARNING
        ]


# VAT Number Regex Patterns by Country
VAT_PATTERNS: Dict[str, str] = {
    "AT": r"^ATU\d{8}$",
    "BE": r"^BE0?\d{9,10}$",
    "BG": r"^BG\d{9,10}$",
    "CY": r"^CY\d{8}[A-Z]$",
    "CZ": r"^CZ\d{8,10}$",
    "DE": r"^DE\d{9}$",
    "DK": r"^DK\d{8}$",
    "EE": r"^EE\d{9}$",
    "EL": r"^EL\d{9}$",  # Greece
    "ES": r"^ES[A-Z0-9]\d{7}[A-Z0-9]$",
    "FI": r"^FI\d{8}$",
    "FR": r"^FR[A-Z0-9]{2}\d{9}$",
    "GB": r"^GB(\d{9}|\d{12}|(GD|HA)\d{3})$",
    "HR": r"^HR\d{11}$",
    "HU": r"^HU\d{8}$",
    "IE": r"^IE\d[A-Z0-9+*]\d{5}[A-Z]{1,2}$",
    "IT": r"^IT\d{11}$",
    "LT": r"^LT(\d{9}|\d{12})$",
    "LU": r"^LU\d{8}$",
    "LV": r"^LV\d{11}$",
    "MT": r"^MT\d{8}$",
    "NL": r"^NL\d{9}B\d{2}$",
    "PL": r"^PL\d{10}$",
    "PT": r"^PT\d{9}$",
    "RO": r"^RO\d{2,10}$",
    "SE": r"^SE\d{12}$",
    "SI": r"^SI\d{8}$",
    "SK": r"^SK\d{10}$",
}


class VATNumberValidator:
    """
    Validates VAT registration numbers.
    
    Performs:
    - Format validation against country-specific patterns
    - Check digit validation where applicable
    - Country code verification
    """
    
    def __init__(self):
        self.patterns = VAT_PATTERNS
    
    def validate(self, vat_number: str) -> ValidationResult:
        """
        Validate a VAT number.
        
        Args:
            vat_number: VAT number to validate
            
        Returns:
            ValidationResult with pass/fail and details
        """
        if not vat_number:
            return ValidationResult(
                rule_id="VAT001",
                rule_name="VAT Number Required",
                passed=False,
                severity=ValidationSeverity.ERROR,
                message="VAT number is empty",
            )
        
        # Clean input
        vat_clean = vat_number.upper().replace(" ", "").replace("-", "")
        
        # Extract country code
        if len(vat_clean) < 2:
            return ValidationResult(
                rule_id="VAT002",
                rule_name="VAT Number Format",
                passed=False,
                severity=ValidationSeverity.ERROR,
                message=f"VAT number too short: {vat_number}",
            )
        
        country_code = vat_clean[:2]
        
        # Handle Greece (EL vs GR)
        if country_code == "GR":
            country_code = "EL"
            vat_clean = "EL" + vat_clean[2:]
        
        # Check if country is supported
        if country_code not in self.patterns:
            return ValidationResult(
                rule_id="VAT003",
                rule_name="Country Code Valid",
                passed=False,
                severity=ValidationSeverity.ERROR,
                message=f"Unknown country code: {country_code}",
            )
        
        # Check pattern
        pattern = self.patterns[country_code]
        if not re.match(pattern, vat_clean):
            return ValidationResult(
                rule_id="VAT004",
                rule_name="VAT Number Pattern",
                passed=False,
                severity=ValidationSeverity.ERROR,
                message=f"Invalid format for {country_code}: {vat_number}",
            )
        
        # Additional check digit validation for specific countries
        if country_code == "DE":
            if not self._validate_de_check_digit(vat_clean[2:]):
                return ValidationResult(
                    rule_id="VAT005",
                    rule_name="Check Digit Valid",
                    passed=False,
                    severity=ValidationSeverity.WARNING,
                    message=f"Check digit validation failed: {vat_number}",
                )
        
        return ValidationResult(
            rule_id="VAT000",
            rule_name="VAT Number Valid",
            passed=True,
            severity=ValidationSeverity.INFO,
            message=f"Valid VAT number: {vat_clean}",
        )
    
    def _validate_de_check_digit(self, number: str) -> bool:
        """Validate German VAT number check digit (MOD 11)."""
        if len(number) != 9:
            return False
        
        try:
            digits = [int(d) for d in number]
        except ValueError:
            return False
        
        # German check digit algorithm
        product = 10
        for i in range(8):
            sum_val = (digits[i] + product) % 10
            if sum_val == 0:
                sum_val = 10
            product = (2 * sum_val) % 11
        
        check_digit = 11 - product
        if check_digit == 10:
            check_digit = 0
        
        return check_digit == digits[8]


class TransactionValidator:
    """
    Validates tax transactions for data quality and compliance.
    """
    
    def __init__(self):
        self.vat_validator = VATNumberValidator()
        self.rules: List[Callable] = []
    
    def add_rule(self, rule: Callable):
        """Add custom validation rule."""
        self.rules.append(rule)
    
    def validate_transaction(
        self,
        transaction: Dict[str, Any],
        transaction_id: str
    ) -> List[ValidationResult]:
        """
        Validate a single transaction.
        
        Args:
            transaction: Transaction data dictionary
            transaction_id: Unique identifier
            
        Returns:
            List of validation results
        """
        results = []
        
        # Required fields
        required_fields = ['date', 'amount', 'country_code']
        for field in required_fields:
            if field not in transaction or transaction[field] is None:
                results.append(ValidationResult(
                    rule_id="TXN001",
                    rule_name="Required Field",
                    passed=False,
                    severity=ValidationSeverity.ERROR,
                    message=f"Missing required field: {field}",
                    field_name=field,
                    record_id=transaction_id,
                ))
        
        # Amount validation
        amount = transaction.get('amount')
        if amount is not None:
            if not isinstance(amount, (int, float, Decimal)):
                results.append(ValidationResult(
                    rule_id="TXN002",
                    rule_name="Amount Numeric",
                    passed=False,
                    severity=ValidationSeverity.ERROR,
                    message=f"Amount must be numeric: {amount}",
                    field_name="amount",
                    record_id=transaction_id,
                ))
            elif amount < 0:
                results.append(ValidationResult(
                    rule_id="TXN003",
                    rule_name="Amount Positive",
                    passed=False,
                    severity=ValidationSeverity.WARNING,
                    message=f"Negative amount: {amount}",
                    field_name="amount",
                    record_id=transaction_id,
                ))
        
        # Date validation
        txn_date = transaction.get('date')
        if txn_date is not None:
            if isinstance(txn_date, str):
                try:
                    txn_date = date.fromisoformat(txn_date)
                except ValueError:
                    results.append(ValidationResult(
                        rule_id="TXN004",
                        rule_name="Date Format",
                        passed=False,
                        severity=ValidationSeverity.ERROR,
                        message=f"Invalid date format: {txn_date}",
                        field_name="date",
                        record_id=transaction_id,
                    ))
            
            if isinstance(txn_date, date) and txn_date > date.today():
                results.append(ValidationResult(
                    rule_id="TXN005",
                    rule_name="Date Not Future",
                    passed=False,
                    severity=ValidationSeverity.WARNING,
                    message=f"Future date: {txn_date}",
                    field_name="date",
                    record_id=transaction_id,
                ))
        
        # VAT number validation if present
        vat_number = transaction.get('vat_number')
        if vat_number:
            vat_result = self.vat_validator.validate(vat_number)
            vat_result.record_id = transaction_id
            vat_result.field_name = "vat_number"
            results.append(vat_result)
        
        # Country code validation
        country = transaction.get('country_code')
        if country:
            valid_countries = set(VAT_PATTERNS.keys()) | {'GB', 'CH', 'NO'}
            if country.upper() not in valid_countries:
                results.append(ValidationResult(
                    rule_id="TXN006",
                    rule_name="Country Code Valid",
                    passed=False,
                    severity=ValidationSeverity.ERROR,
                    message=f"Unknown country code: {country}",
                    field_name="country_code",
                    record_id=transaction_id,
                ))
        
        # Run custom rules
        for rule in self.rules:
            result = rule(transaction, transaction_id)
            if result:
                results.append(result)
        
        # Add success result if no errors
        if not any(not r.passed for r in results):
            results.append(ValidationResult(
                rule_id="TXN000",
                rule_name="Transaction Valid",
                passed=True,
                severity=ValidationSeverity.INFO,
                message="Transaction passed all validations",
                record_id=transaction_id,
            ))
        
        return results
    
    def validate_batch(
        self,
        transactions: List[Dict[str, Any]],
        id_field: str = 'id'
    ) -> ValidationReport:
        """
        Validate multiple transactions.
        
        Args:
            transactions: List of transaction dictionaries
            id_field: Field name for transaction ID
            
        Returns:
            ValidationReport with all results
        """
        report = ValidationReport(
            validated_at=date.today(),
            total_records=len(transactions),
        )
        
        for i, txn in enumerate(transactions):
            txn_id = txn.get(id_field, f"record_{i}")
            results = self.validate_transaction(txn, str(txn_id))
            for result in results:
                report.add_result(result)
        
        return report


def validate_vat_calculation(
    net_amount: Decimal,
    vat_amount: Decimal,
    vat_rate: Decimal,
    tolerance: Decimal = Decimal("0.01")
) -> ValidationResult:
    """
    Validate VAT calculation accuracy.
    
    Args:
        net_amount: Net amount before VAT
        vat_amount: Calculated VAT amount
        vat_rate: VAT rate as percentage
        tolerance: Acceptable rounding tolerance
        
    Returns:
        ValidationResult
    """
    expected_vat = (net_amount * vat_rate / 100).quantize(Decimal("0.01"))
    variance = abs(vat_amount - expected_vat)
    
    if variance <= tolerance:
        return ValidationResult(
            rule_id="CALC001",
            rule_name="VAT Calculation Accurate",
            passed=True,
            severity=ValidationSeverity.INFO,
            message=f"VAT calculation correct: {vat_amount}",
        )
    else:
        return ValidationResult(
            rule_id="CALC001",
            rule_name="VAT Calculation Accurate",
            passed=False,
            severity=ValidationSeverity.ERROR,
            message=f"VAT mismatch: expected {expected_vat}, got {vat_amount}",
        )
