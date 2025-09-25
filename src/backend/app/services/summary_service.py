# services/summary_service.py
import os
import traceback
from typing import Optional
from llama_index.core import StorageContext, load_index_from_storage
#from llama_index.llms.ollama import Ollama
from dotenv import load_dotenv
from llama_index.llms.openai import OpenAI
load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')

class SummaryService:
    def __init__(self):
        #self.llm = Ollama(model="gemma3:12b", request_timeout=600.0)
        self.llm = OpenAI(api_key=api_key)

    def summarize_document(self, file_id: str, max_length: Optional[int] = 500) -> str:
        try:
            index_path = f"index/{file_id}"
            
            if not os.path.exists(index_path):
                raise ValueError(f"Index for file_id {file_id} not found")
            
            storage_context = StorageContext.from_defaults(persist_dir=index_path)
            index = load_index_from_storage(storage_context)
            
            query_engine = index.as_query_engine()
            
            prompt = f"Please provide a concise summary of this document in less than {max_length} words. Focus on the main points and key information."
            response = query_engine.query(prompt)           
            return str(response)
        
        except Exception as e:

            raise Exception(f"Error generating summary: {str(e)}")
