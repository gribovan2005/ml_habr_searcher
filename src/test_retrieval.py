from retrieval import BM25Retriever

def main():
    print("Тестирование BM25 ретривера")
    
    retriever = BM25Retriever()
    
    print("Загружаем документы и обучаем модель")
    retriever.fit()
    
    test_queries = [
        "машинное обучение",
        "python разработка",
        "javascript веб",
        "база данных",
        "искусственный интеллект"
    ]
    
    for query in test_queries:
        print(f"\nПоиск: '{query}'")
        print("-" * 50)
        
        results = retriever.search(query, 5)
        
        for i, (doc_id, score) in enumerate(results, 1):
            try:
                doc = retriever.get_document_by_id(doc_id)
                print(f"{i}. {doc['title']}")
                print(f"   Score: {score:.3f}")
                print(f"   Views: {doc['views']}")
                print(f"   Tags: {', '.join(doc['tags'][:3])}")
                print()
            except Exception as e:
                print(f"Ошибка при получении документа {doc_id}: {e}")

if __name__ == "__main__":
    main()
