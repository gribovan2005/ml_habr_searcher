import axios from 'axios';

const BASE_URL = '/api';

class ApiService {

  async getStats() {
    try {
      const response = await axios.get(`${BASE_URL}/stats`);
      return response.data;
    } catch (error) {
      console.error('Ошибка загрузки статистики:', error);
      throw error;
    }
  }


  async search(query, limit = 10, compare = false) {
    try {
      const response = await axios.post(`${BASE_URL}/search`, {
        query: query.trim(),
        top_n: limit,
        compare: compare
      });
      return response.data;
    } catch (error) {
      console.error('Ошибка поиска:', error);
      throw error;
    }
  }

  async compareSearch(query, limit = 10) {
    try {
      const [mlResponse, bm25Response] = await Promise.all([
        this.search(query, limit, false), 
        this.search(query, limit, true)   
      ]);
      
      return {
        ml: mlResponse.results,
        bm25: bm25Response.results
      };
    } catch (error) {
      console.error('Ошибка сравнительного поиска:', error);
      throw error;
    }
  }

  async getMLStatus() {
    try {
      const response = await axios.get(`${BASE_URL}/ml-model/status`);
      return response.data;
    } catch (error) {
      console.error('Ошибка получения статуса ML модели:', error);
      throw error;
    }
  }
}

export default new ApiService();
