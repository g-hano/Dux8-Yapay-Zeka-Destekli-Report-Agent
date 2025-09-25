import os
import shutil
from typing import Dict, Any
from pathlib import Path

from llama_index.core import VectorStoreIndex, Settings, StorageContext, load_index_from_storage
from llama_index.core.node_parser import SentenceSplitter
from llama_index.readers.file import MarkdownReader
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama

from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')


class RAGService:
    def __init__(self):
        self.data_dir = "data"
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        
        self.index_dir = "index"
        if not os.path.exists(self.index_dir):
            os.makedirs(self.index_dir)
        
        try:
            Settings.embed_model = OllamaEmbedding(model_name="nomic-embed-text:latest")
            Settings.llm = Ollama(model="gemma3:12b", request_timeout=600.0)
            #Settings.embed_model = OpenAIEmbedding(api_key=api_key)
            #Settings.llm = OpenAI(api_key=api_key)
            Settings.text_splitter = SentenceSplitter(chunk_size=512, chunk_overlap=10)
        except Exception as e:
            raise
        
        self.indices = {}
    
    def add_document(self, file_id: str, text: str):
        try:
            file_path = os.path.join(self.data_dir, f"{file_id}.md")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(text)
            
            documents = MarkdownReader().load_data(Path(file_path))
            
            if not documents:
                raise ValueError("No documents were loaded from the markdown file")
            
            storage_context = StorageContext.from_defaults()
            index = VectorStoreIndex.from_documents(
                documents, 
                storage_context=storage_context
            )
            
            index_path = os.path.join(self.index_dir, file_id)
            index.storage_context.persist(persist_dir=index_path)
            
            self.indices[file_id] = index
            
            return f"Document {file_id} is added"
        except Exception as e:
            raise
    
    def load_index(self, file_id: str):
        try:
            if file_id in self.indices:
                return self.indices[file_id]
            
            index_path = os.path.join(self.index_dir, file_id)
            if not os.path.exists(index_path):
                return None
            
            storage_context = StorageContext.from_defaults(persist_dir=index_path)
            
            index = load_index_from_storage(storage_context)
            
            self.indices[file_id] = index
            return index
        
        except Exception as e:
            return None
    
    def query(self, file_id: str, query: str) -> Dict[str, Any]:
        try:
            index = self.load_index(file_id)
            if not index:
                return {
                    "query": query,
                    "answer": "Could not find Index. Upload the file first.",
                    "sources": []
                }
            
            query_engine = index.as_query_engine(similarity_top_k=5)
            
            response = query_engine.query(query)
            
            sources = []
            for node in response.source_nodes:
                sources.append({
                    "text": node.node.text[:200] + "..." if len(node.node.text) > 200 else node.node.text,
                    "score": node.score
                })
            
            
            return {
                "query": query,
                "answer": str(response),
                "sources": sources
            }
        except Exception as e:
            return {
                "query": query,
                "answer": f"Error while querying: {str(e)}",
                "sources": []
            }
    
    def delete_document(self, file_id: str):
        try:
            file_path = os.path.join(self.data_dir, f"{file_id}.md")
            if os.path.exists(file_path):
                os.remove(file_path)
            
            index_path = os.path.join(self.index_dir, file_id)
            if os.path.exists(index_path):
                shutil.rmtree(index_path)
            
            if file_id in self.indices:
                del self.indices[file_id]
            
            return f"Document {file_id} is deleted"
        except Exception as e:
            raise

rag_service = RAGService()

def add_document_to_rag(file_id: str, text: str):
    return rag_service.add_document(file_id, text)

def query_rag(file_id: str, query: str):
    return rag_service.query(file_id, query)

def delete_from_rag(file_id: str):
    return rag_service.delete_document(file_id)