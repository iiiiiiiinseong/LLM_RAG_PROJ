# embedding.py
import os
import json
import glob
from src.config import CONFIG
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

def create_vectorstore_from_all_json(processed_dir: str = CONFIG["paths"]["processed_json_path"],
                                     model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
                                     persist_dir: str = CONFIG["paths"]["chroma_db_path"]):
    """
    processed_dir 폴더 내의 모든 JSON 파일에 대해 'content' 필드의 텍스트를 임베딩하여
    Chroma DB 벡터스토어에 저장합니다. (새 JSON 구조: 최상위에 "documents" 키)
    
    Args:
        processed_dir (str): 전처리된 JSON 파일들이 있는 디렉토리.
        model_name (str): 임베딩 모델 이름.
        persist_dir (str): Chroma DB 저장 디렉토리.
    
    Returns:
        vectorstore: 업데이트된 Chroma DB 벡터스토어 객체.
    """
    record_file = os.path.join(persist_dir, "processed_files.txt")
    if os.path.exists(record_file):
        with open(record_file, "r", encoding="utf-8") as f:
            processed_files = set(line.strip() for line in f if line.strip())
    else:
        processed_files = set()
    
    json_files = glob.glob(os.path.join(processed_dir, "*.json"))
    
    embeddings = HuggingFaceEmbeddings(model_name=model_name)
    vectorstore = Chroma(persist_directory=persist_dir, embedding_function=embeddings)
    
    new_files = []
    total_new_texts = 0
    
    for file_path in json_files:
        file_name = os.path.basename(file_path)
        if file_name in processed_files:
            print(f"이미 처리됨: {file_name}, 스킵합니다.")
            continue
        
        print(f"처리 시작: {file_name}")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                json_data = json.load(f)
                # 새 JSON 구조: 최상위에 "documents" 키
                documents = json_data.get("documents", [])
        except Exception as e:
            print(f"파일 {file_name} 로드 실패: {e}")
            continue
        
        # 'content' 필드에서 텍스트를 추출하고, 메타데이터 및 id 사용
        texts = [doc["content"] for doc in documents if "content" in doc]
        metadatas = [doc.get("metadata", {}) for doc in documents if "content" in doc]
        ids = [doc["id"] for doc in documents if "content" in doc]
        
        if not texts:
            print(f"파일 {file_name}에 'content' 필드가 없거나 데이터가 없습니다. 스킵합니다.")
            continue
        
        # 임베딩 추가
        vectorstore.add_texts(
            texts=texts,
            metadatas=metadatas,
            ids=ids
        )
        
        new_files.append(file_name)
        total_new_texts += len(texts)
        print(f"완료: {file_name} ({len(texts)}개의 문서)")
    
    print(f"ChromaDB에 총 {total_new_texts}개의 신규 문서를 추가했습니다. (경로: {persist_dir})")
    
    if new_files:
        with open(record_file, "a", encoding="utf-8") as f:
            for file_name in new_files:
                f.write(file_name + "\n")
        print(f"처리된 파일 목록 업데이트 완료: {new_files}")
    else:
        print("새로 처리할 파일이 없습니다.")
    
    return vectorstore

def search_vectorstore(query: str,
                       persist_dir: str = "/home/inseong/LLM_RAG_PROJ/data/chroma_db",
                       model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
                       k: int = 3):
    """
    저장된 Chroma DB 벡터스토어에서 쿼리와 유사한 문서를 검색합니다.
    
    Args:
        query (str): 검색할 쿼리 텍스트.
        persist_dir (str): Chroma DB 저장 디렉토리.
        model_name (str): 임베딩 모델 이름.
        k (int): 검색 결과 개수.
    """
    embeddings = HuggingFaceEmbeddings(model_name=model_name)
    vectorstore = Chroma(persist_directory=persist_dir, embedding_function=embeddings)
    results = vectorstore.similarity_search(query, k=k)

    print("검색 결과:")
    for i, result in enumerate(results):
        print(f"Rank {i+1}: {result.page_content}")
        print("-" * 40)

if __name__ == "__main__":
    processed_dir = CONFIG["paths"]["processed_json_path"]
    persist_dir = CONFIG["paths"]["chroma_db_path"]
    vectorstore = create_vectorstore_from_all_json(processed_dir, persist_dir=persist_dir)
