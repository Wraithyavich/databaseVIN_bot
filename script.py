import asyncio
import re
import os
from fastapi import FastAPI, Query, HTTPException
from playwright.async_api import async_playwright
import uvicorn

app = FastAPI()

async def parse_exist(vin: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(f"https://www.exist.ru/price/?q={vin}", timeout=30000)
            # Ждём появления таблицы результатов (селектор может отличаться)
            await page.wait_for_selector(".result-table", timeout=15000)
            content = await page.content()
            # Упрощённый поиск артикулов, которые могут быть турбинами
            # В реальности надо точнее настраивать под структуру сайта
            candidates = re.findall(r'[A-Z0-9]{5,20}', content)
            # Фильтруем по ключевому слову "TURBO" или по номеру детали
            turbo_articles = [c for c in candidates if "TURBO" in c.upper()]
            return list(set(turbo_articles))
        except Exception as e:
            # Логируем ошибку, но не прерываем общий процесс
            print(f"Error parsing Exist: {e}")
            return []
        finally:
            await browser.close()

async def parse_emex(vin: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            # Переходим на страницу поиска Emex
            await page.goto(f"https://www.emex.ru/search?text={vin}", timeout=30000)
            # Ждём появления результатов (селектор нужно подобрать)
            # Например, используем селектор для блока с товарами
            await page.wait_for_selector(".catalog-item", timeout=15000)
            content = await page.content()
            # Здесь нужно извлечь артикулы турбин, возможно, по классу или регулярке
            # Пример: ищем текст внутри элемента с артикулом
            # Упрощённо: все заглавные буквы и цифры от 5 до 20 символов
            candidates = re.findall(r'[A-Z0-9]{5,20}', content)
            turbo_articles = [c for c in candidates if "TURBO" in c.upper()]
            return list(set(turbo_articles))
        except Exception as e:
            print(f"Error parsing Emex: {e}")
            return []
        finally:
            await browser.close()

@app.get("/search")
async def search_vin(vin: str = Query(..., min_length=10)):
    # Запускаем оба парсера параллельно
    exist_task = parse_exist(vin)
    emex_task = parse_emex(vin)
    results = await asyncio.gather(exist_task, emex_task, return_exceptions=True)
    
    articles = []
    for res in results:
        if isinstance(res, list):
            articles.extend(res)
        else:
            # Если произошло исключение, игнорируем
            print(f"Parser error: {res}")
    
    # Убираем дубликаты
    unique_articles = list(set(articles))
    return {"vin": vin, "articles": unique_articles}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    uvicorn.run(app, host="0.0.0.0", port=port)
