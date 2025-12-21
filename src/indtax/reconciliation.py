"""
Payment Reconciliation Module

Matches payments to invoices and identifies discrepancies.
Supports multi-currency reconciliation and tolerance-based matching.

Author: Hatef Tabbakhian
"""

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum
import uuid


class MatchStatus(Enum):
    """Status of reconciliation match."""
    MATCHED = "matched"
    PARTIAL = "partial"
    UNMATCHED = "unmatched"
    OVERPAID = "overpaid"
    TOLERANCE = "matched_within_tolerance"


class Currency(Enum):
    """Supported currencies."""
    EUR = "EUR"
    GBP = "GBP"
    USD = "USD"
    CHF = "CHF"
    SEK = "SEK"
    NOK = "NOK"
    DKK = "DKK"
    PLN = "PLN"
    CZK = "CZK"
    HUF = "HUF"


@dataclass
class Invoice:
    """Represents an invoice for reconciliation."""
    invoice_id: str
    invoice_date: date
    due_date: date
    customer_id: str
    currency: Currency
    net_amount: Decimal
    vat_amount: Decimal
    gross_amount: Decimal
    country_code: str
    description: str = ""
    paid_amount: Decimal = Decimal("0")
    
    def __post_init__(self):
        """Ensure amounts are Decimal."""
        for attr in ['net_amount', 'vat_amount', 'gross_amount', 'paid_amount']:
            value = getattr(self, attr)
            if not isinstance(value, Decimal):
                setattr(self, attr, Decimal(str(value)))
    
    @property
    def outstanding_amount(self) -> Decimal:
        """Calculate outstanding balance."""
        return self.gross_amount - self.paid_amount
    
    @property
    def is_fully_paid(self) -> bool:
        """Check if invoice is fully paid."""
        return self.outstanding_amount <= Decimal("0")
    
    @property
    def is_overdue(self) -> bool:
        """Check if invoice is overdue."""
        return date.today() > self.due_date and not self.is_fully_paid


@dataclass
class Payment:
    """Represents a payment received."""
    payment_id: str
    payment_date: date
    customer_id: str
    currency: Currency
    amount: Decimal
    reference: str
    bank_account: str = ""
    allocated_amount: Decimal = Decimal("0")
    
    def __post_init__(self):
        """Ensure amounts are Decimal."""
        if not isinstance(self.amount, Decimal):
            self.amount = Decimal(str(self.amount))
        if not isinstance(self.allocated_amount, Decimal):
            self.allocated_amount = Decimal(str(self.allocated_amount))
    
    @property
    def unallocated_amount(self) -> Decimal:
        """Calculate unallocated balance."""
        return self.amount - self.allocated_amount


@dataclass
class MatchResult:
    """Result of matching a payment to invoices."""
    payment_id: str
    invoice_id: str
    matched_amount: Decimal
    status: MatchStatus
    variance: Decimal = Decimal("0")
    notes: str = ""


@dataclass
class ReconciliationReport:
    """Summary of reconciliation results."""
    report_date: date
    total_invoices: int
    total_payments: int
    matched_count: int
    unmatched_invoices: int
    unmatched_payments: int
    total_matched_amount: Decimal
    total_variance: Decimal
    matches: List[MatchResult] = field(default_factory=list)
    
    def add_match(self, match: MatchResult):
        """Add a match result to the report."""
        self.matches.append(match)


class PaymentReconciler:
    """
    Payment to Invoice Reconciliation Engine.
    
    Features:
    - Automatic matching by reference
    - Amount-based matching with tolerance
    - Multi-currency support
    - Partial payment handling
    - Overpayment detection
    """
    
    def __init__(
        self,
        tolerance_amount: Decimal = Decimal("0.05"),
        tolerance_percent: Decimal = Decimal("0.01"),
        auto_match_threshold: Decimal = Decimal("1000")
    ):
        """
        Initialize reconciler.
        
        Args:
            tolerance_amount: Max absolute variance to accept
            tolerance_percent: Max percentage variance to accept
            auto_match_threshold: Max amount for automatic matching
        """
        self.tolerance_amount = tolerance_amount
        self.tolerance_percent = tolerance_percent
        self.auto_match_threshold = auto_match_threshold
        self.fx_rates: Dict[Tuple[Currency, Currency], Decimal] = {}
    
    def set_fx_rate(self, from_currency: Currency, to_currency: Currency, rate: Decimal):
        """Set exchange rate for currency conversion."""
        self.fx_rates[(from_currency, to_currency)] = rate
        # Set inverse rate
        self.fx_rates[(to_currency, from_currency)] = (1 / rate).quantize(
            Decimal("0.000001"), rounding=ROUND_HALF_UP
        )
    
    def convert_currency(
        self, 
        amount: Decimal, 
        from_currency: Currency, 
        to_currency: Currency
    ) -> Decimal:
        """
        Convert amount between currencies.
        
        Args:
            amount: Amount to convert
            from_currency: Source currency
            to_currency: Target currency
            
        Returns:
            Converted amount
        """
        if from_currency == to_currency:
            return amount
        
        rate = self.fx_rates.get((from_currency, to_currency))
        if rate is None:
            raise ValueError(f"No FX rate for {from_currency} to {to_currency}")
        
        return (amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    def is_within_tolerance(
        self, 
        expected: Decimal, 
        actual: Decimal
    ) -> Tuple[bool, Decimal]:
        """
        Check if variance is within tolerance.
        
        Args:
            expected: Expected amount
            actual: Actual amount
            
        Returns:
            Tuple of (is_within_tolerance, variance)
        """
        variance = actual - expected
        abs_variance = abs(variance)
        
        # Check absolute tolerance
        if abs_variance <= self.tolerance_amount:
            return True, variance
        
        # Check percentage tolerance
        if expected > 0:
            percent_variance = abs_variance / expected
            if percent_variance <= self.tolerance_percent:
                return True, variance
        
        return False, variance
    
    def match_by_reference(
        self,
        payment: Payment,
        invoices: List[Invoice]
    ) -> Optional[MatchResult]:
        """
        Try to match payment to invoice by reference.
        
        Args:
            payment: Payment to match
            invoices: Available invoices
            
        Returns:
            MatchResult if found, None otherwise
        """
        # Look for invoice ID in payment reference
        for invoice in invoices:
            if invoice.invoice_id in payment.reference:
                if invoice.customer_id == payment.customer_id:
                    return self._create_match(payment, invoice)
        return None
    
    def match_by_amount(
        self,
        payment: Payment,
        invoices: List[Invoice],
        same_customer_only: bool = True
    ) -> Optional[MatchResult]:
        """
        Try to match payment to invoice by amount.
        
        Args:
            payment: Payment to match
            invoices: Available invoices
            same_customer_only: Only match same customer
            
        Returns:
            MatchResult if found, None otherwise
        """
        candidates = []
        
        for invoice in invoices:
            if same_customer_only and invoice.customer_id != payment.customer_id:
                continue
            
            if invoice.is_fully_paid:
                continue
            
            # Convert currency if needed
            try:
                payment_amount = self.convert_currency(
                    payment.unallocated_amount,
                    payment.currency,
                    invoice.currency
                )
            except ValueError:
                continue
            
            within_tol, variance = self.is_within_tolerance(
                invoice.outstanding_amount,
                payment_amount
            )
            
            if within_tol:
                candidates.append((invoice, variance))
        
        if not candidates:
            return None
        
        # Select best match (smallest variance)
        best_invoice, variance = min(candidates, key=lambda x: abs(x[1]))
        return self._create_match(payment, best_invoice, variance)
    
    def _create_match(
        self,
        payment: Payment,
        invoice: Invoice,
        variance: Decimal = Decimal("0")
    ) -> MatchResult:
        """Create a match result."""
        matched_amount = min(payment.unallocated_amount, invoice.outstanding_amount)
        
        if variance != 0:
            status = MatchStatus.TOLERANCE
        elif matched_amount < invoice.outstanding_amount:
            status = MatchStatus.PARTIAL
        elif payment.unallocated_amount > invoice.outstanding_amount:
            status = MatchStatus.OVERPAID
        else:
            status = MatchStatus.MATCHED
        
        return MatchResult(
            payment_id=payment.payment_id,
            invoice_id=invoice.invoice_id,
            matched_amount=matched_amount,
            status=status,
            variance=variance,
        )
    
    def reconcile(
        self,
        invoices: List[Invoice],
        payments: List[Payment]
    ) -> ReconciliationReport:
        """
        Perform full reconciliation.
        
        Args:
            invoices: List of invoices
            payments: List of payments
            
        Returns:
            ReconciliationReport with results
        """
        report = ReconciliationReport(
            report_date=date.today(),
            total_invoices=len(invoices),
            total_payments=len(payments),
            matched_count=0,
            unmatched_invoices=0,
            unmatched_payments=0,
            total_matched_amount=Decimal("0"),
            total_variance=Decimal("0"),
        )
        
        # Create working copies
        working_invoices = list(invoices)
        working_payments = list(payments)
        
        # First pass: match by reference
        for payment in working_payments[:]:
            match = self.match_by_reference(payment, working_invoices)
            if match:
                self._apply_match(match, working_invoices, working_payments)
                report.add_match(match)
                report.matched_count += 1
                report.total_matched_amount += match.matched_amount
                report.total_variance += match.variance
        
        # Second pass: match by amount
        for payment in working_payments[:]:
            if payment.unallocated_amount > 0:
                match = self.match_by_amount(payment, working_invoices)
                if match:
                    self._apply_match(match, working_invoices, working_payments)
                    report.add_match(match)
                    report.matched_count += 1
                    report.total_matched_amount += match.matched_amount
                    report.total_variance += match.variance
        
        # Count unmatched
        report.unmatched_invoices = sum(
            1 for inv in working_invoices if not inv.is_fully_paid
        )
        report.unmatched_payments = sum(
            1 for pmt in working_payments if pmt.unallocated_amount > 0
        )
        
        return report
    
    def _apply_match(
        self,
        match: MatchResult,
        invoices: List[Invoice],
        payments: List[Payment]
    ):
        """Apply match to update invoice and payment states."""
        for invoice in invoices:
            if invoice.invoice_id == match.invoice_id:
                invoice.paid_amount += match.matched_amount
                break
        
        for payment in payments:
            if payment.payment_id == match.payment_id:
                payment.allocated_amount += match.matched_amount
                break


def generate_aging_report(
    invoices: List[Invoice],
    as_of_date: Optional[date] = None
) -> Dict[str, Dict[str, Decimal]]:
    """
    Generate accounts receivable aging report.
    
    Args:
        invoices: List of invoices
        as_of_date: Date to calculate aging from
        
    Returns:
        Aging buckets by customer
    """
    if as_of_date is None:
        as_of_date = date.today()
    
    aging: Dict[str, Dict[str, Decimal]] = {}
    
    for invoice in invoices:
        if invoice.is_fully_paid:
            continue
        
        customer = invoice.customer_id
        if customer not in aging:
            aging[customer] = {
                "current": Decimal("0"),
                "1_30_days": Decimal("0"),
                "31_60_days": Decimal("0"),
                "61_90_days": Decimal("0"),
                "over_90_days": Decimal("0"),
                "total": Decimal("0"),
            }
        
        days_overdue = (as_of_date - invoice.due_date).days
        outstanding = invoice.outstanding_amount
        
        if days_overdue <= 0:
            aging[customer]["current"] += outstanding
        elif days_overdue <= 30:
            aging[customer]["1_30_days"] += outstanding
        elif days_overdue <= 60:
            aging[customer]["31_60_days"] += outstanding
        elif days_overdue <= 90:
            aging[customer]["61_90_days"] += outstanding
        else:
            aging[customer]["over_90_days"] += outstanding
        
        aging[customer]["total"] += outstanding
    
    return aging
