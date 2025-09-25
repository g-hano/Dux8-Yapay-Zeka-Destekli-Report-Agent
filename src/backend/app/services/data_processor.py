import polars as pl
from typing import Dict, Any, List
import os
import numpy as np

class DataProcessor:
    def __init__(self):
        pass
    
    def read_file(self, file_path: str) -> pl.DataFrame:
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.csv':
            return pl.read_csv(file_path)
        elif file_ext == '.tsv':
            return pl.read_csv(file_path, separator='\t')
        elif file_ext in ['.xlsx', '.xls']:
            return pl.read_excel(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")
    
    def get_data_summary(self, df: pl.DataFrame) -> Dict[str, Any]:
        return {
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": df.columns if isinstance(df.columns, list) else df.columns.tolist(),
            "data_types": {col: str(df[col].dtype) for col in df.columns},
            "null_counts": {col: df[col].null_count() for col in df.columns}
        }
    
    def calculate_kpis(self, df: pl.DataFrame) -> Dict[str, Any]:
        """Calculate basic KPIs for the data"""
        kpis = {}
        
        numeric_cols = [col for col in df.columns if df[col].dtype in [pl.Float32, pl.Float64, pl.Int8, pl.Int16, pl.Int32, pl.Int64]]
        
        statistics = {}
        for col in numeric_cols:
            col_data = df[col].drop_nulls()
            if len(col_data) > 0:
                statistics[col] = [
                    col_data.min(),
                    col_data.max(),
                    col_data.mean(),
                    col_data.median(),
                    col_data.std()
                ]
        
        kpis["statistics"] = statistics
        
        categorical_cols = [col for col in df.columns if df[col].dtype in [pl.Utf8, pl.Object]]
        
        categorical = {}
        for col in categorical_cols:
            categorical[col] = {
                "unique_count": df[col].n_unique(),
                "most_common": df[col].mode()[0] if len(df[col]) > 0 else None
            }
        
        kpis["categorical"] = categorical
        
        return kpis
    
    def identify_trends(self, df: pl.DataFrame) -> Dict[str, Any]:
        """Identify basic trends in the data"""
        trends = {}
        
        numeric_cols = [col for col in df.columns if df[col].dtype in [pl.Float32, pl.Float64, pl.Int8, pl.Int16, pl.Int32, pl.Int64]]
        
        for col in numeric_cols:
            col_data = df[col].drop_nulls()
            if len(col_data) > 1:
                first_val = col_data[0]
                last_val = col_data[-1]
                
                if last_val > first_val:
                    direction = "increasing"
                elif last_val < first_val:
                    direction = "decreasing"
                else:
                    direction = "stable"
                
                if len(col_data) > 2:
                    x = list(range(len(col_data)))
                    y = col_data.to_list()
                    correlation = np.corrcoef(x, y)[0, 1] if len(x) > 1 else 0
                else:
                    correlation = 0
                
                trends[col] = {
                    "trend": direction,
                    "correlation": correlation,
                    "first_value": float(first_val),
                    "last_value": float(last_val)
                }
        
        return trends
    
    def generate_sample_data(self, df: pl.DataFrame) -> List[Dict[str, Any]]:
        """Generate sample data for preview"""
        return [
            df.head(5).to_dict(as_series=False),
            df.tail(5).to_dict(as_series=False)
        ]