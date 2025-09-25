from pydantic import BaseModel
from typing import Optional
import os
import json
from datetime import datetime
#from llama_index.llms.ollama import Ollama
from llama_index.llms.openai import OpenAI
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')

class SummaryRequest(BaseModel):
    """Schema for summary API request"""
    file_id: str
    max_length: Optional[int] = 500

class SummaryResponse(BaseModel):
    """Schema for summary API response"""
    file_id: str
    summary: str


class SummaryService:
    def __init__(self):
        #self.llm = Ollama(model="gemma3:12b", request_timeout=60.0)
        self.llm = OpenAI(api_key=api_key)
        self.summaries_dir = "summaries"
        if not os.path.exists(self.summaries_dir):
            os.makedirs(self.summaries_dir)
    
    def summarize_text(self, text: str, max_length: int = 500) -> str:
        prompt = f"""
        Please summarize the following text. The summary should not exceed {max_length} words and should include the main idea of the text.
        
        Text:
        {text}
        
        Summary:
        """
        
        response = self.llm.complete(prompt)
        return str(response)
    
    def summarize_document(self, file_id: str) -> str:
        file_path = f"data/{file_id}.md"
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
            
            summary = self.summarize_text(text)
            return summary
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {file_path}")
        except Exception as e:
            raise Exception(f"Summarization error: {str(e)}")
    
    def save_summary(self, file_id: str, summary: str):
        summary_path = os.path.join(self.summaries_dir, f"{file_id}.json")
        
        summary_data = {
            "file_id": file_id,
            "summary": summary,
            "created_at": datetime.now().isoformat()
        }
        
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, ensure_ascii=False, indent=2)
        
        return summary_path
    
    def load_summary(self, file_id: str):
        summary_path = os.path.join(self.summaries_dir, f"{file_id}.json")
        
        if not os.path.exists(summary_path):
            return None
        
        with open(summary_path, "r", encoding="utf-8") as f:
            summary_data = json.load(f)
        

        return summary_data
