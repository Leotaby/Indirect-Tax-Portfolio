"""
Tax Reporting Module

Generates VAT returns, EC Sales Lists, and compliance reports.
Supports multiple EU jurisdictions and filing formats.

Author: Hatef Tabbakhian
"""

import csv
import json
from dataclasses import dataclass, asdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum

from .vat_calculator import VATCalculation, VATRate, EU_VAT_RATES


class ReportFormat(Enum):
    """Output format for reports."""
    CSV = "csv"
    JSON = "json"
    XML = "xml"


class ReportPeriod(Enum):
    """VAT return filing period."""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


@dataclass
class VATReturnLine:
    """Single line in a VAT return."""
    box_number: str
    description: str
    amount: Decimal
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "box": self.box_number,
            "description": self.description,
            "amount": float(self.amount),
        }


@dataclass
class VATReturn:
    """VAT Return for a jurisdiction."""
    country_code: str
    period_start: date
    period_end: date
    submission_deadline: date
    lines: List[VATReturnLine]
    total_output_vat: Decimal
    total_input_vat: Decimal
    net_vat_due: Decimal
    status: str = "draft"
    
    @property
    def is_refund(self) -> bool:
        """Check if return results in refund."""
        return self.net_vat_due < 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "country_code": self.country_code,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "submission_deadline": self.submission_deadline.isoformat(),
            "lines": [line.to_dict() for line in self.lines],
            "total_output_vat": float(self.total_output_vat),
            "total_input_vat": float(self.total_input_vat),
            "net_vat_due": float(self.net_vat_due),
            "status": self.status,
        }


@dataclass
class ECSalesLine:
    """EC Sales List entry for intra-EU B2B supplies."""
    customer_vat_number: str
    customer_country: str
    total_value: Decimal
    indicator: str = "S"  # S=Services, G=Goods, T=Triangulation
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "customer_vat": self.customer_vat_number,
            "country": self.customer_country,
            "value": float(self.total_value),
            "indicator": self.indicator,
        }


@dataclass
class ECSalesList:
    """EC Sales List report."""
    country_code: str
    period_start: date
    period_end: date
    submission_deadline: date
    lines: List[ECSalesLine]
    total_goods: Decimal
    total_services: Decimal
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "country_code": self.country_code,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "submission_deadline": self.submission_deadline.isoformat(),
            "lines": [line.to_dict() for line in self.lines],
            "total_goods": float(self.total_goods),
            "total_services": float(self.total_services),
        }


class VATReturnGenerator:
    """
    Generates VAT returns for EU jurisdictions.
    
    Supports:
    - Standard UK VAT return (Box 1-9)
    - German VAT return (UStVA)
    - Generic EU format
    """
    
    def __init__(self, country_code: str):
        """Initialize for specific country."""
        self.country_code = country_code
        self.country_name = EU_VAT_RATES.get(
            country_code, 
            type('', (), {'country_name': country_code})()
        ).country_name
    
    def generate_uk_vat_return(
        self,
        period_start: date,
        period_end: date,
        sales_calculations: List[VATCalculation],
        purchase_calculations: List[VATCalculation],
        ec_sales: Decimal = Decimal("0"),
        ec_purchases: Decimal = Decimal("0"),
    ) -> VATReturn:
        """
        Generate UK VAT return format.
        
        Box 1: VAT due on sales
        Box 2: VAT due on EC acquisitions
        Box 3: Total VAT due (1 + 2)
        Box 4: VAT reclaimed on purchases
        Box 5: Net VAT (3 - 4)
        Box 6: Total sales (ex VAT)
        Box 7: Total purchases (ex VAT)
        Box 8: EC supplies (ex VAT)
        Box 9: EC acquisitions (ex VAT)
        """
        # Calculate totals
        output_vat = sum(c.vat_amount for c in sales_calculations)
        input_vat = sum(c.vat_amount for c in purchase_calculations)
        total_sales = sum(c.net_amount for c in sales_calculations)
        total_purchases = sum(c.net_amount for c in purchase_calculations)
        
        ec_acquisition_vat = (ec_purchases * Decimal("0.20")).quantize(Decimal("0.01"))
        
        lines = [
            VATReturnLine("1", "VAT due on sales", output_vat),
            VATReturnLine("2", "VAT due on EC acquisitions", ec_acquisition_vat),
            VATReturnLine("3", "Total VAT due", output_vat + ec_acquisition_vat),
            VATReturnLine("4", "VAT reclaimed on purchases", input_vat),
            VATReturnLine("5", "Net VAT due/refund", output_vat + ec_acquisition_vat - input_vat),
            VATReturnLine("6", "Total sales ex VAT", total_sales),
            VATReturnLine("7", "Total purchases ex VAT", total_purchases),
            VATReturnLine("8", "EC supplies ex VAT", ec_sales),
            VATReturnLine("9", "EC acquisitions ex VAT", ec_purchases),
        ]
        
        # Calculate submission deadline (1 month + 7 days after period end)
        deadline = date(
            period_end.year + (1 if period_end.month == 12 else 0),
            (period_end.month % 12) + 1,
            7
        )
        
        return VATReturn(
            country_code="GB",
            period_start=period_start,
            period_end=period_end,
            submission_deadline=deadline,
            lines=lines,
            total_output_vat=output_vat + ec_acquisition_vat,
            total_input_vat=input_vat,
            net_vat_due=output_vat + ec_acquisition_vat - input_vat,
        )
    
    def generate_generic_eu_return(
        self,
        period_start: date,
        period_end: date,
        sales_calculations: List[VATCalculation],
        purchase_calculations: List[VATCalculation],
    ) -> VATReturn:
        """Generate generic EU VAT return format."""
        output_vat = sum(c.vat_amount for c in sales_calculations)
        input_vat = sum(c.vat_amount for c in purchase_calculations)
        total_sales = sum(c.net_amount for c in sales_calculations)
        total_purchases = sum(c.net_amount for c in purchase_calculations)
        
        # Group by rate
        sales_by_rate: Dict[Decimal, Decimal] = {}
        for calc in sales_calculations:
            rate = calc.vat_rate
            sales_by_rate[rate] = sales_by_rate.get(rate, Decimal("0")) + calc.net_amount
        
        lines = []
        for rate, amount in sorted(sales_by_rate.items(), reverse=True):
            vat = (amount * rate / 100).quantize(Decimal("0.01"))
            lines.append(VATReturnLine(
                f"sales_{rate}",
                f"Sales at {rate}% rate",
                amount
            ))
            lines.append(VATReturnLine(
                f"vat_{rate}",
                f"VAT at {rate}%",
                vat
            ))
        
        lines.extend([
            VATReturnLine("total_output", "Total Output VAT", output_vat),
            VATReturnLine("total_input", "Total Input VAT", input_vat),
            VATReturnLine("net_due", "Net VAT Due", output_vat - input_vat),
        ])
        
        return VATReturn(
            country_code=self.country_code,
            period_start=period_start,
            period_end=period_end,
            submission_deadline=period_end,  # Varies by country
            lines=lines,
            total_output_vat=output_vat,
            total_input_vat=input_vat,
            net_vat_due=output_vat - input_vat,
        )


class ReportExporter:
    """Export reports to various formats."""
    
    def __init__(self, output_dir: Path):
        """Initialize with output directory."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export_vat_return(
        self,
        vat_return: VATReturn,
        format: ReportFormat = ReportFormat.JSON,
        filename: Optional[str] = None
    ) -> Path:
        """
        Export VAT return to file.
        
        Args:
            vat_return: VAT return to export
            format: Output format
            filename: Custom filename (optional)
            
        Returns:
            Path to exported file
        """
        if filename is None:
            filename = f"vat_return_{vat_return.country_code}_{vat_return.period_end}"
        
        if format == ReportFormat.JSON:
            return self._export_json(vat_return.to_dict(), f"{filename}.json")
        elif format == ReportFormat.CSV:
            return self._export_vat_csv(vat_return, f"{filename}.csv")
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def export_ec_sales_list(
        self,
        ec_list: ECSalesList,
        format: ReportFormat = ReportFormat.CSV,
        filename: Optional[str] = None
    ) -> Path:
        """Export EC Sales List."""
        if filename is None:
            filename = f"ec_sales_{ec_list.country_code}_{ec_list.period_end}"
        
        if format == ReportFormat.CSV:
            return self._export_ecsl_csv(ec_list, f"{filename}.csv")
        elif format == ReportFormat.JSON:
            return self._export_json(ec_list.to_dict(), f"{filename}.json")
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _export_json(self, data: Dict[str, Any], filename: str) -> Path:
        """Export data to JSON file."""
        filepath = self.output_dir / filename
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        return filepath
    
    def _export_vat_csv(self, vat_return: VATReturn, filename: str) -> Path:
        """Export VAT return to CSV."""
        filepath = self.output_dir / filename
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Box", "Description", "Amount"])
            for line in vat_return.lines:
                writer.writerow([line.box_number, line.description, line.amount])
        return filepath
    
    def _export_ecsl_csv(self, ec_list: ECSalesList, filename: str) -> Path:
        """Export EC Sales List to CSV."""
        filepath = self.output_dir / filename
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Customer VAT Number", "Country", "Value", "Indicator"])
            for line in ec_list.lines:
                writer.writerow([
                    line.customer_vat_number,
                    line.customer_country,
                    line.total_value,
                    line.indicator
                ])
        return filepath


def generate_vat_summary_pivot(
    calculations: List[VATCalculation],
    group_by: str = "country"
) -> Dict[str, Dict[str, Decimal]]:
    """
    Generate pivot table summary of VAT calculations.
    
    Args:
        calculations: List of VAT calculations
        group_by: Field to group by (country, rate, month)
        
    Returns:
        Pivot table as nested dictionary
    """
    pivot: Dict[str, Dict[str, Decimal]] = {}
    
    for calc in calculations:
        if group_by == "country":
            key = calc.country_code
        elif group_by == "rate":
            key = f"{calc.vat_rate}%"
        else:
            key = "all"
        
        if key not in pivot:
            pivot[key] = {
                "net_total": Decimal("0"),
                "vat_total": Decimal("0"),
                "gross_total": Decimal("0"),
                "count": Decimal("0"),
            }
        
        pivot[key]["net_total"] += calc.net_amount
        pivot[key]["vat_total"] += calc.vat_amount
        pivot[key]["gross_total"] += calc.gross_amount
        pivot[key]["count"] += 1
    
    return pivot
