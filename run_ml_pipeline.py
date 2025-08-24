import os
import sys
import subprocess
import logging
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_command(command: str, description: str, cwd: str = None) -> bool:
    
    logger.info(f"{description}")
    logger.info(f"Команда: {command}")
    
    try:
        start_time = time.time()
        result = subprocess.run(
            command, 
            shell=True, 
            check=True, 
            capture_output=True, 
            text=True,
            cwd=cwd
        )
        
        duration = time.time() - start_time
        logger.info(f"{description} завершен успешно за {duration:.1f}с")
        
        if result.stdout.strip():
            logger.info(f"Output: {result.stdout.strip()}")
            
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"{description} завершился с ошибкой")
        logger.error(f"Код возврата: {e.returncode}")
        logger.error(f"Stderr: {e.stderr}")
        if e.stdout:
            logger.error(f"Stdout: {e.stdout}")
        return False


def check_requirements():
    logger.info("Проверка требований")
    
    required_dirs = ['src', 'data']
    required_files = ['src/db_manager.py']
    
    missing = []
    
    for dir_name in required_dirs:
        if not os.path.exists(dir_name):
            missing.append(f"Директория: {dir_name}")
    
    for file_name in required_files:
        if not os.path.exists(file_name):
            missing.append(f"Файл: {file_name}")
    
    if missing:
        logger.error(" Отсутствуют необходимые компоненты:")
        for item in missing:
            logger.error(f"  - {item}")
        return False
    
    os.makedirs('data', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    return True


def run_ml_pipeline():
    
    logger.info("ML Pipeline")

    
    if not check_requirements():
        logger.error("Не удалось выполнить проверку требований")
        return False
    
    src_dir = "src"
    
    success = run_command(
        "python dataset_creation.py",
        "Создание обучающего датасета",
        cwd=src_dir
    )
    if not success:
        logger.error("Ошибка на этапе создания датасета")
        return False
    
    if not os.path.exists('data/training_dataset.parquet'):
        logger.error("Датасет не был создан")
        return False
    
    success = run_command(
        "python feature_generator.py", 
        "Генерация признаков",
        cwd=src_dir
    )
    if not success:
        logger.error("Ошибка на этапе генерации признаков")
        return False
    
    if not os.path.exists('data/training_features.parquet'):
        logger.error("Признаки не были созданы")
        return False
    
    success = run_command(
        "python train.py",
        "Обучение LGBMRanker модели",
        cwd=src_dir
    )
    if not success:
        logger.error("Ошибка на этапе обучения модели")
        return False
    
    if not os.path.exists('data/lgbm_ranker_final.pkl'):
        logger.error("Модель не была сохранена")
        return False
    
    logger.info("ML Pipeline завершен")

    
    data_files = []
    for file in Path('data').glob('*'):
        if file.is_file():
            size = file.stat().st_size / (1024 * 1024)
            data_files.append(f"{file.name} ({size:.1f} MB)")
    
    logger.info("Созданные файлы:")
    for file_info in data_files:
        logger.info(file_info)
    
    
    return True


def main():
    try:
        success = run_ml_pipeline()
        if success:
            logger.info("Пайплайн выполнен успешно")
            return 0
        else:
            logger.error("Пайплайн завершился с ошибками")
            return 1
            
    except KeyboardInterrupt:
        logger.info("Пайплайн прерван пользователем")
        return 1
    except Exception as e:
        logger.error(f"Непредвиденная ошибка: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
