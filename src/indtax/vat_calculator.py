"""
VAT Calculator Module

Handles VAT liability calculations for EMEA jurisdictions.
Supports standard, reduced, and zero rates across multiple countries.

Author: Hatef Tabbakhian
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Dict, List, Optional
from datetime import date


class VATRate(Enum):
    """VAT rate types across EU jurisdictions."""
    STANDARD = "standard"
    REDUCED = "reduced"
    SUPER_REDUCED = "super_reduced"
    ZERO = "zero"
    EXEMPT = "exempt"


@dataclass
class CountryVATRates:
    """VAT rates for a specific country."""
    country_code: str
    country_name: str
    standard_rate: Decimal
    reduced_rate: Optional[Decimal] = None
    super_reduced_rate: Optional[Decimal] = None
    parking_rate: Optional[Decimal] = None
    
    def get_rate(self, rate_type: VATRate) -> Decimal:
        """Get the VAT rate for a specific type."""
        rates = {
            VATRate.STANDARD: self.standard_rate,
            VATRate.REDUCED: self.reduced_rate or self.standard_rate,
            VATRate.SUPER_REDUCED: self.super_reduced_rate or self.reduced_rate or self.standard_rate,
            VATRate.ZERO: Decimal("0"),
            VATRate.EXEMPT: Decimal("0"),
        }
        return rates.get(rate_type, self.standard_rate)


# EU VAT Rates Database (2024)
EU_VAT_RATES: Dict[str, CountryVATRates] = {
    "DE": CountryVATRates("DE", "Germany", Decimal("19"), Decimal("7")),
    "FR": CountryVATRates("FR", "France", Decimal("20"), Decimal("10"), Decimal("5.5")),
    "IT": CountryVATRates("IT", "Italy", Decimal("22"), Decimal("10"), Decimal("4")),
    "ES": CountryVATRates("ES", "Spain", Decimal("21"), Decimal("10"), Decimal("4")),
    "NL": CountryVATRates("NL", "Netherlands", Decimal("21"), Decimal("9")),
    "BE": CountryVATRates("BE", "Belgium", Decimal("21"), Decimal("12"), Decimal("6")),
    "AT": CountryVATRates("AT", "Austria", Decimal("20"), Decimal("13"), Decimal("10")),
    "PT": CountryVATRates("PT", "Portugal", Decimal("23"), Decimal("13"), Decimal("6")),
    "PL": CountryVATRates("PL", "Poland", Decimal("23"), Decimal("8"), Decimal("5")),
    "SE": CountryVATRates("SE", "Sweden", Decimal("25"), Decimal("12"), Decimal("6")),
    "DK": CountryVATRates("DK", "Denmark", Decimal("25")),
    "FI": CountryVATRates("FI", "Finland", Decimal("24"), Decimal("14"), Decimal("10")),
    "IE": CountryVATRates("IE", "Ireland", Decimal("23"), Decimal("13.5"), Decimal("9")),
    "GR": CountryVATRates("GR", "Greece", Decimal("24"), Decimal("13"), Decimal("6")),
    "CZ": CountryVATRates("CZ", "Czech Republic", Decimal("21"), Decimal("15"), Decimal("10")),
    "RO": CountryVATRates("RO", "Romania", Decimal("19"), Decimal("9"), Decimal("5")),
    "HU": CountryVATRates("HU", "Hungary", Decimal("27"), Decimal("18"), Decimal("5")),
    "SK": CountryVATRates("SK", "Slovakia", Decimal("20"), Decimal("10")),
    "BG": CountryVATRates("BG", "Bulgaria", Decimal("20"), Decimal("9")),
    "HR": CountryVATRates("HR", "Croatia", Decimal("25"), Decimal("13"), Decimal("5")),
    "LU": CountryVATRates("LU", "Luxembourg", Decimal("17"), Decimal("14"), Decimal("8")),
    "SI": CountryVATRates("SI", "Slovenia", Decimal("22"), Decimal("9.5")),
    "LT": CountryVATRates("LT", "Lithuania", Decimal("21"), Decimal("9"), Decimal("5")),
    "LV": CountryVATRates("LV", "Latvia", Decimal("21"), Decimal("12"), Decimal("5")),
    "EE": CountryVATRates("EE", "Estonia", Decimal("22"), Decimal("9")),
    "CY": CountryVATRates("CY", "Cyprus", Decimal("19"), Decimal("9"), Decimal("5")),
    "MT": CountryVATRates("MT", "Malta", Decimal("18"), Decimal("7"), Decimal("5")),
    # Non-EU EMEA
    "GB": CountryVATRates("GB", "United Kingdom", Decimal("20"), Decimal("5")),
    "CH": CountryVATRates("CH", "Switzerland", Decimal("8.1"), Decimal("2.6")),
    "NO": CountryVATRates("NO", "Norway", Decimal("25"), Decimal("15"), Decimal("12")),
}


@dataclass
class Transaction:
    """Represents a taxable transaction."""
    transaction_id: str
    date: date
    country_code: str
    net_amount: Decimal
    rate_type: VATRate
    description: str
    customer_vat_number: Optional[str] = None
    is_reverse_charge: bool = False
    
    def __post_init__(self):
        """Ensure net_amount is Decimal."""
        if not isinstance(self.net_amount, Decimal):
            self.net_amount = Decimal(str(self.net_amount))


@dataclass
class VATCalculation:
    """Result of VAT calculation for a transaction."""
    transaction_id: str
    country_code: str
    net_amount: Decimal
    vat_rate: Decimal
    vat_amount: Decimal
    gross_amount: Decimal
    is_reverse_charge: bool
    
    @property
    def effective_rate(self) -> Decimal:
        """Calculate effective VAT rate."""
        if self.net_amount == 0:
            return Decimal("0")
        return (self.vat_amount / self.net_amount * 100).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )


class VATCalculator:
    """
    VAT Calculator for EMEA transactions.
    
    Handles:
    - Standard VAT calculations
    - Reverse charge mechanism (B2B cross-border)
    - Multiple rate types
    - Rounding per EU regulations
    """
    
    def __init__(self, rates: Optional[Dict[str, CountryVATRates]] = None):
        """Initialize with VAT rates database."""
        self.rates = rates or EU_VAT_RATES
    
    def get_vat_rate(self, country_code: str, rate_type: VATRate) -> Decimal:
        """
        Get VAT rate for a country and rate type.
        
        Args:
            country_code: ISO 2-letter country code
            rate_type: Type of VAT rate to apply
            
        Returns:
            VAT rate as percentage (e.g., 19 for 19%)
            
        Raises:
            ValueError: If country code not found
        """
        if country_code not in self.rates:
            raise ValueError(f"Unknown country code: {country_code}")
        return self.rates[country_code].get_rate(rate_type)
    
    def calculate_vat(self, transaction: Transaction) -> VATCalculation:
        """
        Calculate VAT for a single transaction.
        
        Args:
            transaction: Transaction details
            
        Returns:
            VATCalculation with computed amounts
        """
        # Get applicable rate
        vat_rate = self.get_vat_rate(transaction.country_code, transaction.rate_type)
        
        # Reverse charge: VAT rate is 0 for accounting but recorded
        if transaction.is_reverse_charge:
            vat_amount = Decimal("0")
        else:
            # Calculate VAT: net * (rate / 100)
            vat_amount = (transaction.net_amount * vat_rate / 100).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        
        gross_amount = transaction.net_amount + vat_amount
        
        return VATCalculation(
            transaction_id=transaction.transaction_id,
            country_code=transaction.country_code,
            net_amount=transaction.net_amount,
            vat_rate=vat_rate,
            vat_amount=vat_amount,
            gross_amount=gross_amount,
            is_reverse_charge=transaction.is_reverse_charge,
        )
    
    def calculate_batch(self, transactions: List[Transaction]) -> List[VATCalculation]:
        """
        Calculate VAT for multiple transactions.
        
        Args:
            transactions: List of transactions
            
        Returns:
            List of VATCalculation results
        """
        return [self.calculate_vat(t) for t in transactions]
    
    def calculate_vat_liability(
        self, 
        calculations: List[VATCalculation],
        group_by_country: bool = True
    ) -> Dict[str, Dict[str, Decimal]]:
        """
        Calculate total VAT liability from calculations.
        
        Args:
            calculations: List of VAT calculations
            group_by_country: Whether to group by country
            
        Returns:
            Dictionary with liability summary
        """
        if group_by_country:
            liability: Dict[str, Dict[str, Decimal]] = {}
            
            for calc in calculations:
                if calc.country_code not in liability:
                    liability[calc.country_code] = {
                        "net_total": Decimal("0"),
                        "vat_total": Decimal("0"),
                        "gross_total": Decimal("0"),
                        "transaction_count": Decimal("0"),
                    }
                
                liability[calc.country_code]["net_total"] += calc.net_amount
                liability[calc.country_code]["vat_total"] += calc.vat_amount
                liability[calc.country_code]["gross_total"] += calc.gross_amount
                liability[calc.country_code]["transaction_count"] += 1
            
            return liability
        else:
            return {
                "total": {
                    "net_total": sum(c.net_amount for c in calculations),
                    "vat_total": sum(c.vat_amount for c in calculations),
                    "gross_total": sum(c.gross_amount for c in calculations),
                    "transaction_count": Decimal(len(calculations)),
                }
            }
    
    def validate_vat_number(self, vat_number: str) -> bool:
        """
        Basic VAT number format validation.
        
        Args:
            vat_number: VAT registration number
            
        Returns:
            True if format is valid
        """
        if not vat_number or len(vat_number) < 4:
            return False
        
        country_code = vat_number[:2].upper()
        number_part = vat_number[2:]
        
        # Check country code exists
        if country_code not in self.rates:
            return False
        
        # Check number part is alphanumeric
        if not number_part.replace(" ", "").isalnum():
            return False
        
        return True


def calculate_reverse_charge_applicable(
    supplier_country: str,
    customer_country: str,
    customer_vat_number: Optional[str],
    is_b2b: bool
) -> bool:
    """
    Determine if reverse charge mechanism applies.
    
    Reverse charge applies for B2B cross-border transactions
    within the EU where customer has valid VAT number.
    
    Args:
        supplier_country: Supplier's country code
        customer_country: Customer's country code
        customer_vat_number: Customer's VAT registration number
        is_b2b: Whether transaction is B2B
        
    Returns:
        True if reverse charge applies
    """
    # Same country - no reverse charge
    if supplier_country == customer_country:
        return False
    
    # Must be B2B
    if not is_b2b:
        return False
    
    # Customer must have VAT number
    if not customer_vat_number:
        return False
    
    # Both must be in EU (simplified check)
    eu_countries = {
        "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
        "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
        "PL", "PT", "RO", "SK", "SI", "ES", "SE"
    }
    
    if supplier_country not in eu_countries or customer_country not in eu_countries:
        return False
    
    return True
