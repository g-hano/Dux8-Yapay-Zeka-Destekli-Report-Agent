from llama_index.llms.ollama import Ollama
from llama_index.llms.openai import OpenAI
from typing import Dict, Any
import json
import os
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')

class ActionItemsService:
    def __init__(self):
        self.llm = Ollama(model="gemma3:12b", request_timeout=120.0)
        #self.llm = OpenAI(api_key=api_key)
    
    def _get_trends_as_dict(self, trends: Any) -> Dict[str, Dict[str, Any]]:
        if isinstance(trends, dict):
            return trends
        elif isinstance(trends, list):
            trends_dict = {}
            for item in trends:
                if isinstance(item, dict):
                    col = item.get('column')
                    if col:
                        trend_data = {k: v for k, v in item.items() if k != 'column'}
                        trends_dict[col] = trend_data
            return trends_dict
        return {}
    
    def generate_action_items(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        formatted_results = self._format_analysis_results(analysis_results)
        
        prompt = self._create_action_items_prompt(formatted_results)
        
        response = self.llm.complete(prompt)
        
        try:
            action_items = self._parse_llm_response(str(response))
            return action_items
        except Exception as e:
            return self._create_fallback_actions(analysis_results, str(response))
    
    def _format_analysis_results(self, results: Dict[str, Any]) -> str:
        formatted = []
        
        if 'summary' in results:
            summary = results['summary']
            formatted.append(f"📊 DATA SUMMARY:")
            
            rows = summary.get('rows', 0)
            cols = summary.get('columns', 0)
            formatted.append(f"- Total rows: {rows}")
            formatted.append(f"- Number of columns: {cols}")
            
            columns = summary.get('column_names', [])
            if columns:
                col_preview = ', '.join(map(str, columns[:5]))
                if len(columns) > 5:
                    col_preview += " ..."
                formatted.append(f"- Columns: {col_preview}")
        
        if 'kpis' in results:
            formatted.append(f"\n📈 KPI ANALYSIS:")
            kpis = results['kpis']
            
            if 'statistics' in kpis:
                formatted.append("- Statistical Summary:")
                stats = kpis['statistics']
                if isinstance(stats, dict):
                    for key, values in stats.items():
                        if isinstance(values, list) and len(values) > 2:
                            try:
                                mean_value = float(values[2]) if values[2] is not None else 0.0
                                formatted.append(f"  * {key}: Average {mean_value:.2f}")
                            except (ValueError, TypeError):
                                formatted.append(f"  * {key}: {values[2]}")
                            except IndexError:
                                formatted.append(f"  * {key}: {values[0] if len(values) > 0 else 'N/A'}")
                        else:
                            formatted.append(f"  * {key}: Insufficient data")
                else:
                    formatted.append("- Statistical Summary: Insufficient data")
            
            if 'categorical' in kpis:
                formatted.append("- Categorical Analysis:")
                categorical = kpis['categorical']
                if isinstance(categorical, dict):
                    for col, data in categorical.items():
                        if isinstance(data, dict) and 'unique_count' in data:
                            try:
                                unique_count = int(data['unique_count'])
                                formatted.append(f"  * {col}: {unique_count} unique values")
                            except (ValueError, TypeError):
                                formatted.append(f"  * {col}: {data['unique_count']} unique values")
                else:
                    formatted.append("- Categorical Analysis: Insufficient data")
        
        if 'trends' in results:
            formatted.append(f"\n📊 TREND ANALYSIS:")
            trends_dict = self._get_trends_as_dict(results['trends'])
            for col, trend_data in trends_dict.items():
                if isinstance(trend_data, dict) and 'trend' in trend_data:
                    trend = trend_data['trend']
                    if trend == 'increasing':
                        formatted.append(f"  * {col}: ↗️ INCREASING trend")
                    elif trend == 'decreasing':
                        formatted.append(f"  * {col}: ↘️ DECREASING trend")
                    else:
                        formatted.append(f"  * {col}: ➡️ STABLE trend")
                    
                    if 'correlation' in trend_data and trend_data['correlation'] is not None:
                        try:
                            corr_value = float(trend_data['correlation'])
                            formatted.append(f"    (Correlation: {corr_value:.3f})")
                        except (ValueError, TypeError):
                            pass
        
        if 'sample_data' in results:
            try:
                sample_data = results['sample_data']
                if isinstance(sample_data, list) and len(sample_data) > 0:
                    sample = sample_data[0]
                    if isinstance(sample, dict):
                        formatted.append(f"\n📝 SAMPLE DATA:")
                        for key, value in list(sample.items())[:3]:  # İlk 3 sütun
                            if value is None:
                                value_str = "N/A"
                            elif isinstance(value, (int, float)):
                                try:
                                    if isinstance(value, float) and value.is_integer():
                                        value_str = str(int(value))
                                    else:
                                        value_str = f"{value:.2f}" if isinstance(value, float) else str(value)
                                except:
                                    value_str = str(value)
                            else:
                                value_str = str(value)
                            
                            formatted.append(f"  * {key}: {value_str}")
                elif isinstance(sample_data, dict) and len(sample_data) > 0:
                    formatted.append(f"\n📝 SAMPLE DATA:")
                    for key in list(sample_data.keys())[:3]:
                        values = sample_data[key]
                        value = values[0] if isinstance(values, list) and len(values) > 0 else values

                        if value is None:
                            value_str = "N/A"
                        elif isinstance(value, (int, float)):
                            try:
                                if isinstance(value, float) and value.is_integer():
                                    value_str = str(int(value))
                                else:
                                    value_str = f"{value:.2f}" if isinstance(value, float) else str(value)
                            except:
                                value_str = str(value)
                        else:
                            value_str = str(value)
                        
                        formatted.append(f"  * {key}: {value_str}")
            except Exception:
                pass
        
        return "\n".join(formatted)
    
    def _create_action_items_prompt(self, formatted_results: str) -> str:
        """Action items için prompt oluştur"""
        return f"""
Based on the following data analysis results, suggest concrete action items for business.

{formatted_results}

Please respond in the following JSON format:

{{
    "action_items": [
        {{
            "priority": "high|medium|low",
            "category": "performance|optimization|risk|opportunity|data_quality",
            "title": "Short title",
            "description": "Detailed description",
            "expected_impact": "Expected impact",
            "timeline": "Time frame (e.g.: 1 week, 1 month)",
            "responsible": "Who should be responsible"
        }}
    ],
    "summary": "General evaluation and recommendations summary",
    "key_insights": [
        "Key finding 1",
        "Key finding 2",
        "Key finding 3"
    ]
}}

Action items should focus on:
- Performance improvements
- Risk reduction
- Evaluating opportunities
- Data quality improvement
- Operational optimization

Each action item should be concrete, measurable, and actionable.
"""
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        start_idx = response.find('{')
        end_idx = response.rfind('}') + 1
        
        if start_idx == -1 or end_idx == 0:
            raise ValueError("JSON not found")
        
        json_str = response[start_idx:end_idx]
        
        parsed = json.loads(json_str)
        
        if 'action_items' not in parsed:
            raise ValueError("action_items not found")
        
        return parsed
    
    def _create_fallback_actions(self, results: Dict[str, Any], llm_response: str) -> Dict[str, Any]:
        fallback_actions = []
        
        if 'trends' in results:
            trends_dict = self._get_trends_as_dict(results['trends'])
            for col, trend_data in trends_dict.items():
                if isinstance(trend_data, dict) and 'trend' in trend_data:
                    if trend_data['trend'] == 'decreasing':
                        fallback_actions.append({
                            "priority": "high",
                            "category": "performance",
                            "title": f"Investigate the decrease in {col} values",
                            "description": f"A decreasing trend detected in {col} metric. Analyze the reasons.",
                            "expected_impact": "Performance improvement",
                            "timeline": "2 weeks",
                            "responsible": "Analysis team"
                        })
                    elif trend_data['trend'] == 'increasing':
                        fallback_actions.append({
                            "priority": "medium",
                            "category": "opportunity",
                            "title": f"Sustain the increase in {col} values",
                            "description": f"There is a positive trend in {col} metric. Develop strategies to sustain this increase.",
                            "expected_impact": "Growth momentum",
                            "timeline": "1 month",
                            "responsible": "Strategy team"
                        })
        
        if 'summary' in results and 'null_counts' in results['summary']:
            null_counts = results['summary']['null_counts']
            if isinstance(null_counts, dict):
                for col, count in null_counts.items():
                    try:
                        count_int = int(count) if count is not None else 0
                        if count_int > 0:
                            fallback_actions.append({
                                "priority": "medium",
                                "category": "data_quality",
                                "title": f"Complete missing data in {col} column",
                                "description": f"{count_int} missing data detected in {col} column.",
                                "expected_impact": "Data quality increase",
                                "timeline": "1 week",
                                "responsible": "Data team"
                            })
                    except (ValueError, TypeError):
                        if count:
                            fallback_actions.append({
                                "priority": "medium",
                                "category": "data_quality",
                                "title": f"Check data quality in {col} column",
                                "description": f"Data quality issues detected in {col} column.",
                                "expected_impact": "Data quality increase",
                                "timeline": "1 week",
                                "responsible": "Data team"
                            })
        
        return {
            "action_items": fallback_actions,
            "summary": "Action items created based on automatic analysis results.",
            "key_insights": [
                "Data analysis completed",
                "Trend analyses reviewed", 
                "Action items determined"
            ],
            "note": "LLM response could not be parsed, fallback actions used"
        }

    def generate_prioritized_actions(self, analysis_results: Dict[str, Any], business_context: str = "") -> Dict[str, Any]:
        basic_actions = self.generate_action_items(analysis_results)
        
        if not business_context:
            return basic_actions
        
        context_prompt = f"""
Reprioritize the existing action items according to the following business context:

Business Context: {business_context}

Existing Action Items: {json.dumps(basic_actions, ensure_ascii=False, indent=2)}

Please respond in the same JSON format, but with priorities updated according to the business context.
"""
        
        response = self.llm.complete(context_prompt)
        
        try:
            return self._parse_llm_response(str(response))
        except:
            return basic_actions