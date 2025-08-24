import time
import logging
import requests
import json
from typing import List, Dict, Any
from tqdm import tqdm
from bs4 import BeautifulSoup
import re
from elasticsearch_manager import ElasticsearchManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HabrDataCollector:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.base_url = "https://habr.com"
    
    def fetch_articles(self, max_pages: int = 50) -> List[Dict[str, Any]]:
        articles_data = []
        
        logger.info(f"Начинаем сбор данных с {max_pages} страниц Habr")
        
        rss_urls = self._get_articles_from_rss(max_pages)
        logger.info(f"Найдено {len(rss_urls)} статей в RSS")
        
        fresh_urls = self._get_fresh_articles_from_pages(max_pages=3)
        logger.info(f"Найдено {len(fresh_urls)} свежих статей со страниц")
        

        all_urls = list(set(rss_urls + fresh_urls))
        article_urls = all_urls
        
        if not article_urls:
            logger.warning("Не удалось получить статьи ни из RSS, ни со страниц")
            return []
        
        logger.info(f"Всего найдено {len(article_urls)} уникальных статей для обработки")
        
        for url in tqdm(article_urls, desc="Обработка статей"):
            try:
                article_data = self._scrape_article_page(url)
                if article_data:
                    articles_data.append(article_data)
                
                time.sleep(1)
                
            except Exception as e:
                logger.warning(f"Ошибка при обработке статьи {url}: {e}")
                continue
        
        logger.info(f"Сбор завершен. Получено {len(articles_data)} статей.")
        return articles_data
    
    def _get_articles_from_rss(self, max_pages: int = 50) -> List[str]:

        urls = []
        
        rss_feeds = [
            "https://habr.com/ru/rss/articles/?fl=ru",  
            "https://habr.com/ru/rss/flows/develop/",   
            "https://habr.com/ru/rss/flows/admin/",     
            "https://habr.com/ru/rss/flows/design/",    
            "https://habr.com/ru/rss/flows/management/", 
            "https://habr.com/ru/rss/hubs/python/",     
            "https://habr.com/ru/rss/hubs/javascript/", 
            "https://habr.com/ru/rss/hubs/ai/",         
        ]
        
        logger.info(f"Собираем статьи из {len(rss_feeds)} RSS фидов...")
        
        for rss_url in rss_feeds:
            try:
                logger.info(f"Обрабатываем фид: {rss_url}")
                response = self.session.get(rss_url, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'xml')
                
                items = soup.find_all('item')
                for item in items:
                    guid = item.find('guid')
                    if guid and guid.text not in urls:
                        urls.append(guid.text)
                
                time.sleep(1)  
                
            except Exception as e:
                logger.warning(f"Ошибка при получении RSS {rss_url}: {e}")
                continue
        
        logger.info(f"Найдено {len(urls)} уникальных статей из всех фидов")
        return urls[:max_pages * 5]  
    
    def _get_fresh_articles_from_pages(self, max_pages: int = 3) -> List[str]:

        urls = []
        
        fresh_pages = [
            "https://habr.com/ru/articles/",              
            "https://habr.com/ru/articles/top/daily/",    
            "https://habr.com/ru/flows/develop/",         
            "https://habr.com/ru/flows/admin/",           
        ]
        
        logger.info(f"Парсим свежие статьи со страниц...")
        
        for page_url in fresh_pages:
            try:
                for page in range(1, max_pages + 1):
                    url = f"{page_url}page{page}/" if page > 1 else page_url
                    
                    logger.info(f"Обрабатываем страницу: {url}")
                    response = self.session.get(url, timeout=10)
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    

                    article_links = soup.find_all('a', class_='tm-title__link')
                    
                    for link in article_links:
                        href = link.get('href')
                        if href and href.startswith('/'):
                            full_url = f"https://habr.com{href}"
                            if full_url not in urls:
                                urls.append(full_url)
                    
                    time.sleep(1)  
                    
            except Exception as e:
                logger.warning(f"Ошибка при парсинге страницы {page_url}: {e}")
                continue
        
        logger.info(f"Найдено {len(urls)} свежих статей со страниц")
        return urls
    
    def _scrape_article_page(self, url: str) -> Dict[str, Any]:
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            article_id = url.split('/')[-2] if url.endswith('/') else url.split('/')[-1]
            
            title_elem = soup.find('h1', class_='tm-title')
            if not title_elem:
                title_elem = soup.find('h1', class_='tm-article-snippet__title-link')
            title = title_elem.get_text(strip=True) if title_elem else "Без заголовка"
            
            article_body = soup.find('div', class_='tm-article-body')
            text_content = ""
            if article_body:
                for script in article_body(["script", "style"]):
                    script.decompose()
                text_content = article_body.get_text(strip=True)
            
            tags = []
            hub_links = soup.find_all('a', class_='tm-publication-hub__link')
            for hub in hub_links:
                tag = hub.get_text(strip=True)
                if tag:
                    tags.append(tag)
            
            views = 0
            score = 0
            comments_count = 0
            
            stats_elem = soup.find('div', class_='tm-article-snippet__stats')
            if stats_elem:
                views_elem = stats_elem.find('span', class_='tm-icon-counter__value')
                if views_elem:
                    views_text = views_elem.get_text(strip=True)
                    views = self._extract_number(views_text)
                
                score = 0
                
                comments_count = 0
            
            return {
                'id': article_id,
                'url': url,
                'title': title,
                'text_content': text_content,
                'tags': tags,
                'views': views,
                'score': score,
                'comments_count': comments_count
            }
            
        except Exception as e:
            logger.warning(f"Ошибка при парсинге статьи {url}: {e}")
            return None
    
    def _extract_number(self, text: str) -> int:

        if not text:
            return 0
        
        numbers = re.findall(r'\d+', text.replace(' ', ''))
        if numbers:
            return int(numbers[0])
        
        return 0
    
    def fetch_articles_by_hub(self, hub_alias: str, max_pages: int = 10) -> List[Dict[str, Any]]:

        articles_data = []
        
        logger.info(f"Начинаем сбор данных из хаба '{hub_alias}' с {max_pages} страниц...")
        
        try:
            rss_url = f"https://habr.com/ru/rss/hub/{hub_alias}/?fl=ru"
            response = self.session.get(rss_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'xml')
            urls = []
            

            items = soup.find_all('item')
            for item in items:
                guid = item.find('guid')
                if guid:
                    urls.append(guid.text)
            

            urls = urls[:max_pages * 20]
            
            logger.info(f"Найдено {len(urls)} статей в хабе '{hub_alias}'")
            

            for url in tqdm(urls, desc=f"Обработка статей из хаба {hub_alias}"):
                try:
                    article_data = self._scrape_article_page(url)
                    if article_data:
                        articles_data.append(article_data)
                    

                    time.sleep(1)
                    
                except Exception as e:
                    logger.warning(f"Ошибка при обработке статьи {url}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Ошибка при получении статей из хаба '{hub_alias}': {e}")
        
        logger.info(f"Сбор из хаба '{hub_alias}' завершен. Получено {len(articles_data)} статей.")
        return articles_data


def main():

    collector = HabrDataCollector()
    

    print("Собираем статьи со всех страниц...")
    all_articles = collector.fetch_articles(max_pages=5) 
    
    if all_articles:
        print(f"\nСобрано {len(all_articles)} статей.")
        print("\nПример первой статьи:")
        first_article = all_articles[0]
        print(f"ID: {first_article['id']}")
        print(f"Заголовок: {first_article['title']}")
        print(f"URL: {first_article['url']}")
        print(f"Просмотры: {first_article['views']}")
        print(f"Рейтинг: {first_article['score']}")
        print(f"Комментарии: {first_article['comments_count']}")
        print(f"Теги: {first_article['tags']}")
        print(f"Длина текста: {len(first_article['text_content'])} символов")
    else:
        print("Не удалось собрать статьи.")


if __name__ == "__main__":
    main()
