"""
Unit Tests for Indirect Tax Portfolio

Run with: pytest tests/ -v
"""

import pytest
from decimal import Decimal
from datetime import date

import sys
sys.path.insert(0, 'src')

from indtax import (
    VATCalculator,
    VATRate,
    Transaction,
    VATNumberValidator,
    PaymentReconciler,
    Invoice,
    Payment,
    Currency,
    MatchStatus,
    TransactionValidator,
    ValidationSeverity,
    validate_vat_calculation,
)


class TestVATCalculator:
    """Tests for VAT calculation functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = VATCalculator()
    
    def test_german_standard_rate(self):
        """Test German standard VAT rate (19%)."""
        rate = self.calculator.get_vat_rate("DE", VATRate.STANDARD)
        assert rate == Decimal("19")
    
    def test_german_reduced_rate(self):
        """Test German reduced VAT rate (7%)."""
        rate = self.calculator.get_vat_rate("DE", VATRate.REDUCED)
        assert rate == Decimal("7")
    
    def test_uk_standard_rate(self):
        """Test UK standard VAT rate (20%)."""
        rate = self.calculator.get_vat_rate("GB", VATRate.STANDARD)
        assert rate == Decimal("20")
    
    def test_calculate_simple_vat(self):
        """Test simple VAT calculation."""
        transaction = Transaction(
            transaction_id="TEST001",
            date=date.today(),
            country_code="DE",
            net_amount=Decimal("100.00"),
            rate_type=VATRate.STANDARD,
            description="Test transaction",
        )
        
        result = self.calculator.calculate_vat(transaction)
        
        assert result.net_amount == Decimal("100.00")
        assert result.vat_rate == Decimal("19")
        assert result.vat_amount == Decimal("19.00")
        assert result.gross_amount == Decimal("119.00")
    
    def test_calculate_vat_with_rounding(self):
        """Test VAT calculation with rounding."""
        transaction = Transaction(
            transaction_id="TEST002",
            date=date.today(),
            country_code="DE",
            net_amount=Decimal("99.99"),
            rate_type=VATRate.STANDARD,
            description="Test rounding",
        )
        
        result = self.calculator.calculate_vat(transaction)
        
        # 99.99 * 0.19 = 18.9981, rounded to 19.00
        assert result.vat_amount == Decimal("19.00")
    
    def test_reverse_charge(self):
        """Test reverse charge mechanism."""
        transaction = Transaction(
            transaction_id="TEST003",
            date=date.today(),
            country_code="DE",
            net_amount=Decimal("1000.00"),
            rate_type=VATRate.STANDARD,
            description="Reverse charge",
            is_reverse_charge=True,
        )
        
        result = self.calculator.calculate_vat(transaction)
        
        assert result.vat_amount == Decimal("0")
        assert result.gross_amount == Decimal("1000.00")
        assert result.is_reverse_charge is True
    
    def test_zero_rate(self):
        """Test zero-rated transaction."""
        transaction = Transaction(
            transaction_id="TEST004",
            date=date.today(),
            country_code="GB",
            net_amount=Decimal("500.00"),
            rate_type=VATRate.ZERO,
            description="Zero rated",
        )
        
        result = self.calculator.calculate_vat(transaction)
        
        assert result.vat_amount == Decimal("0")
        assert result.gross_amount == Decimal("500.00")
    
    def test_batch_calculation(self):
        """Test batch VAT calculation."""
        transactions = [
            Transaction("T1", date.today(), "DE", Decimal("100"), VATRate.STANDARD, "Test 1"),
            Transaction("T2", date.today(), "FR", Decimal("200"), VATRate.STANDARD, "Test 2"),
            Transaction("T3", date.today(), "IT", Decimal("300"), VATRate.STANDARD, "Test 3"),
        ]
        
        results = self.calculator.calculate_batch(transactions)
        
        assert len(results) == 3
        assert results[0].vat_rate == Decimal("19")  # DE
        assert results[1].vat_rate == Decimal("20")  # FR
        assert results[2].vat_rate == Decimal("22")  # IT
    
    def test_liability_summary(self):
        """Test VAT liability summary by country."""
        transactions = [
            Transaction("T1", date.today(), "DE", Decimal("100"), VATRate.STANDARD, "DE 1"),
            Transaction("T2", date.today(), "DE", Decimal("200"), VATRate.STANDARD, "DE 2"),
            Transaction("T3", date.today(), "FR", Decimal("300"), VATRate.STANDARD, "FR 1"),
        ]
        
        results = self.calculator.calculate_batch(transactions)
        liability = self.calculator.calculate_vat_liability(results, group_by_country=True)
        
        assert "DE" in liability
        assert "FR" in liability
        assert liability["DE"]["net_total"] == Decimal("300")
        assert liability["FR"]["net_total"] == Decimal("300")
    
    def test_unknown_country_raises(self):
        """Test that unknown country raises ValueError."""
        with pytest.raises(ValueError, match="Unknown country code"):
            self.calculator.get_vat_rate("XX", VATRate.STANDARD)


class TestVATNumberValidator:
    """Tests for VAT number validation."""
    
    def setup_method(self):
        self.validator = VATNumberValidator()
    
    def test_valid_german_vat(self):
        """Test valid German VAT number."""
        result = self.validator.validate("DE123456789")
        assert result.passed is True
    
    def test_valid_french_vat(self):
        """Test valid French VAT number."""
        result = self.validator.validate("FR12345678901")
        assert result.passed is True
    
    def test_valid_uk_vat(self):
        """Test valid UK VAT number."""
        result = self.validator.validate("GB123456789")
        assert result.passed is True
    
    def test_invalid_format(self):
        """Test invalid VAT number format."""
        result = self.validator.validate("DE12345")  # Too short
        assert result.passed is False
        assert result.severity == ValidationSeverity.ERROR
    
    def test_unknown_country(self):
        """Test unknown country code."""
        result = self.validator.validate("XX123456789")
        assert result.passed is False
    
    def test_empty_vat_number(self):
        """Test empty VAT number."""
        result = self.validator.validate("")
        assert result.passed is False
    
    def test_greece_el_code(self):
        """Test Greek VAT with EL prefix."""
        result = self.validator.validate("EL123456789")
        assert result.passed is True


class TestPaymentReconciliation:
    """Tests for payment reconciliation."""
    
    def setup_method(self):
        self.reconciler = PaymentReconciler(
            tolerance_amount=Decimal("0.05"),
            tolerance_percent=Decimal("0.01"),
        )
    
    def test_exact_match(self):
        """Test exact amount matching."""
        invoices = [
            Invoice(
                invoice_id="INV001",
                invoice_date=date(2024, 1, 1),
                due_date=date(2024, 1, 31),
                customer_id="CUST001",
                currency=Currency.EUR,
                net_amount=Decimal("100.00"),
                vat_amount=Decimal("19.00"),
                gross_amount=Decimal("119.00"),
                country_code="DE",
            )
        ]
        
        payments = [
            Payment(
                payment_id="PMT001",
                payment_date=date(2024, 1, 15),
                customer_id="CUST001",
                currency=Currency.EUR,
                amount=Decimal("119.00"),
                reference="INV001",
            )
        ]
        
        report = self.reconciler.reconcile(invoices, payments)
        
        assert report.matched_count == 1
        assert report.unmatched_invoices == 0
        assert report.unmatched_payments == 0
    
    def test_tolerance_match(self):
        """Test matching within tolerance."""
        invoices = [
            Invoice(
                invoice_id="INV002",
                invoice_date=date(2024, 1, 1),
                due_date=date(2024, 1, 31),
                customer_id="CUST001",
                currency=Currency.EUR,
                net_amount=Decimal("100.00"),
                vat_amount=Decimal("19.00"),
                gross_amount=Decimal("119.00"),
                country_code="DE",
            )
        ]
        
        payments = [
            Payment(
                payment_id="PMT002",
                payment_date=date(2024, 1, 15),
                customer_id="CUST001",
                currency=Currency.EUR,
                amount=Decimal("119.03"),  # Within 0.05 tolerance
                reference="Payment for INV002",
            )
        ]
        
        report = self.reconciler.reconcile(invoices, payments)
        
        assert report.matched_count == 1
        assert report.matches[0].status == MatchStatus.TOLERANCE
    
    def test_unmatched_payment(self):
        """Test unmatched payment detection."""
        invoices = []
        payments = [
            Payment(
                payment_id="PMT003",
                payment_date=date(2024, 1, 15),
                customer_id="CUST001",
                currency=Currency.EUR,
                amount=Decimal("500.00"),
                reference="Unknown",
            )
        ]
        
        report = self.reconciler.reconcile(invoices, payments)
        
        assert report.matched_count == 0
        assert report.unmatched_payments == 1


class TestTransactionValidator:
    """Tests for transaction validation."""
    
    def setup_method(self):
        self.validator = TransactionValidator()
    
    def test_valid_transaction(self):
        """Test validation of valid transaction."""
        transaction = {
            "id": "TXN001",
            "date": "2024-01-15",
            "amount": 1000.00,
            "country_code": "DE",
        }
        
        results = self.validator.validate_transaction(transaction, "TXN001")
        errors = [r for r in results if not r.passed]
        
        assert len(errors) == 0
    
    def test_missing_required_field(self):
        """Test detection of missing required field."""
        transaction = {
            "id": "TXN002",
            "amount": 1000.00,
            # Missing 'date' and 'country_code'
        }
        
        results = self.validator.validate_transaction(transaction, "TXN002")
        errors = [r for r in results if not r.passed]
        
        assert len(errors) >= 2
    
    def test_negative_amount_warning(self):
        """Test warning for negative amount."""
        transaction = {
            "id": "TXN003",
            "date": "2024-01-15",
            "amount": -100.00,
            "country_code": "DE",
        }
        
        results = self.validator.validate_transaction(transaction, "TXN003")
        warnings = [r for r in results if r.severity == ValidationSeverity.WARNING]
        
        assert len(warnings) >= 1


class TestVATCalculationValidation:
    """Tests for VAT calculation validation."""
    
    def test_correct_calculation(self):
        """Test validation of correct VAT calculation."""
        result = validate_vat_calculation(
            net_amount=Decimal("100.00"),
            vat_amount=Decimal("19.00"),
            vat_rate=Decimal("19"),
        )
        
        assert result.passed is True
    
    def test_incorrect_calculation(self):
        """Test detection of incorrect VAT calculation."""
        result = validate_vat_calculation(
            net_amount=Decimal("100.00"),
            vat_amount=Decimal("20.00"),  # Should be 19.00
            vat_rate=Decimal("19"),
        )
        
        assert result.passed is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
