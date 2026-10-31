from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ReportExportRequest(BaseModel):
    portfolio_id: int
    format: str = "csv"  # csv or pdf
    include_trades: bool = True
    include_performance: bool = True
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class DataQualityReport(BaseModel):
    total_rows_processed: int
    valid_rows_inserted: int
    skipped_rows_count: int
    symbols_count: int
    date_start: str
    date_end: str
    missing_value_anomalies: List[str]
    zero_volume_count: int
    status: str
